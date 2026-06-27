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

    @abstractmethod
    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Core business logic for the agent."""
        pass

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Resilient fallback path for the agent (e.g. Chaos Monkey self-healing)."""
        await notify_agent_event(WSEventTypes.AGENT_RECOVERED, self.name, data={"status": "recovered", "msg": "Using fallback data"})
        return {"status": "success", "msg": f"{self.name} recovered from simulated failure via cached state."}
