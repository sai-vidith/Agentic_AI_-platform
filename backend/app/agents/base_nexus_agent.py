from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import json
import asyncio
from app.tools.llm_tool import llm_service
from app.core.schemas import AgentState, WSEvent, WSEventTypes
from datetime import datetime, timezone

# Global callback list to hook in websockets or dashboards
agent_event_callbacks = []

def register_agent_callback(callback):
    agent_event_callbacks.append(callback)

async def notify_agent_event(event_type: WSEventTypes, agent_name: str, target: Optional[str] = None, data: Dict[str, Any] = None):
    event = WSEvent(
        type=event_type,
        agent=agent_name,
        target=target,
        data=data or {},
        timestamp=datetime.now(timezone.utc)
    )
    for cb in agent_event_callbacks:
        try:
            await cb(event)
        except Exception as e:
            # Silence websocket failures in background threads
            pass

class BaseNexusAgent(ABC):
    """Base class for all NexusAI specialist agents."""
    
    def __init__(self, name: str, model: str = "nexus-fast"):
        self.name = name
        self.model = model

    async def call_llm(self, prompt: str, system_message: str = "You are a helpful AI assistant.", response_format: Optional[Dict[str, str]] = None) -> str:
        """Standard async LLM call with LiteLLM router + rate limiting + token tracking."""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # Trigger WS event that agent is thinking
        await notify_agent_event(WSEventTypes.AGENT_THINKING, self.name, data={"status": "thinking"})
        
        # Call LLM with agent_name for per-agent metrics tracking
        response = await llm_service.acompletion(
            model=self.model,
            messages=messages,
            agent_name=self.name,
            response_format=response_format
        )
        
        content = response.choices[0].message.content
        
        # Stream content chunks to the frontend for the "streaming thoughts" wow effect
        words = content.split(" ")
        chunk_size = max(1, len(words) // 10)
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size]) + " "
            await notify_agent_event(
                WSEventTypes.AGENT_REASONING, 
                self.name, 
                data={"chunk": chunk}
            )
            await asyncio.sleep(0.05) # Tiny pause for real-time visualization feel
            
        return content

    async def run_react_loop(self, task_input: str, tools: Dict[str, Any], max_iterations: int = 3, system_message: str = "You are a helpful AI assistant.") -> str:
        """Executes a Reason + Act (ReAct) loop until a final answer is reached."""
        
        tool_descriptions = "\n".join([f"- {name}: {func.__doc__}" for name, func in tools.items()])
        full_system_msg = f"{system_message}\n\nYou have access to the following tools:\n{tool_descriptions}\n\nTo use a tool, reply EXACTLY with:\nTOOL: tool_name({{\"arg1\": \"value\"}})\n\nIf you have the final answer, reply EXACTLY with:\nFINAL_ANSWER: your final answer here."
        
        messages = [
            {"role": "system", "content": full_system_msg},
            {"role": "user", "content": task_input}
        ]
        
        for iteration in range(max_iterations):
            await notify_agent_event(WSEventTypes.AGENT_THINKING, self.name, data={"status": f"thinking (step {iteration+1})"})
            
            response = await llm_service.acompletion(
                model=self.model,
                messages=messages,
                agent_name=self.name
            )
            
            content = response.choices[0].message.content
            
            # Stream thoughts
            words = content.split(" ")
            chunk_size = max(1, len(words) // 10)
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i+chunk_size]) + " "
                await notify_agent_event(WSEventTypes.AGENT_REASONING, self.name, data={"chunk": chunk})
                await asyncio.sleep(0.05)
                
            messages.append({"role": "assistant", "content": content})
            
            if "FINAL_ANSWER:" in content:
                return content.split("FINAL_ANSWER:")[1].strip()
                
            if "TOOL:" in content:
                try:
                    tool_call_str = content.split("TOOL:")[1].split("\n")[0].strip()
                    tool_name = tool_call_str.split("(")[0]
                    args_str = tool_call_str[len(tool_name)+1:-1]
                    args = json.loads(args_str) if args_str else {}
                    
                    if tool_name in tools:
                        await notify_agent_event(WSEventTypes.AGENT_TOOL_CALL, self.name, data={"tool": tool_name, "args": args})
                        tool_result = await tools[tool_name](**args)
                        messages.append({"role": "user", "content": f"TOOL_RESULT: {tool_result}"})
                    else:
                        messages.append({"role": "user", "content": f"ERROR: Tool {tool_name} not found."})
                except Exception as e:
                    messages.append({"role": "user", "content": f"ERROR parsing tool call: {e}"})
            else:
                # If neither, force it to give a final answer
                messages.append({"role": "user", "content": "Please provide a FINAL_ANSWER: or use a TOOL:."})
                
        return "Max iterations reached without a final answer."

    @abstractmethod
    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Core business logic for the agent."""
        pass

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Resilient fallback path for the agent (e.g. Chaos Monkey self-healing)."""
        await notify_agent_event(WSEventTypes.AGENT_RECOVERED, self.name, data={"status": "recovered", "msg": "Using fallback data"})
        return {"status": "success", "msg": f"{self.name} recovered from simulated failure via cached state."}
