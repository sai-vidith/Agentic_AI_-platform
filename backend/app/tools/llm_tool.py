import asyncio
import os
import random
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from litellm import Router
from app.config import settings
from app.core.rate_limiter import AsyncRateLimiter
from app.observability.metrics import metrics_collector

def is_real_key(key: str, provider: str) -> bool:
    if not key:
        return False
    key_lower = key.lower()
    if "your_" in key_lower or "mock" in key_lower or "key_here" in key_lower:
        return False
    if provider == "groq" and not key.startswith("gsk_"):
        return False
    if provider == "gemini" and not (key.startswith("AIza") or key.startswith("AQ.")):
        return False
    return True

# Initialize rate limiters for safety
groq_limiter = AsyncRateLimiter(max_rpm=25)
gemini_limiter = AsyncRateLimiter(max_rpm=15)

class LLMService:
    """LiteLLM Completion service with automatic failovers, rate limiters, and token tracking."""
    
    def __init__(self):
        # Configure model parameters
        model_list = []
        
        # GitHub Models (OpenAI Compatible)
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("github_pat"):
            model_list.append({
                "model_name": "nexus-fast",
                "litellm_params": {
                    "model": "openai/gpt-4o",
                    "api_key": settings.OPENAI_API_KEY,
                    "api_base": settings.OPENAI_API_BASE
                }
            })
            model_list.append({
                "model_name": "nexus-shadow",
                "litellm_params": {
                    "model": "openai/gpt-4o-mini",
                    "api_key": settings.OPENAI_API_KEY,
                    "api_base": settings.OPENAI_API_BASE
                }
            })
        
        # Groq
        if is_real_key(settings.GROQ_API_KEY, "groq"):
            model_list.append({
                "model_name": "nexus-fast",
                "litellm_params": {
                    "model": "groq/llama-3.3-70b-versatile",
                    "api_key": settings.GROQ_API_KEY
                }
            })
            model_list.append({
                "model_name": "nexus-shadow",
                "litellm_params": {
                    "model": "groq/llama-3.1-8b-instant",
                    "api_key": settings.GROQ_API_KEY
                }
            })
            
        # Cerebras - DISABLED (model llama-3.3-70b not available on free tier)
        # if is_real_key(settings.CEREBRAS_API_KEY, "cerebras"):
        #     model_list.append({
        #         "model_name": "nexus-fast",
        #         "litellm_params": {
        #             "model": "cerebras/llama-3.3-70b",
        #             "api_key": settings.CEREBRAS_API_KEY,
        #         }
        #     })
            
        # Gemini
        if is_real_key(settings.GEMINI_API_KEY, "gemini"):
            model_list.append({
                "model_name": "nexus-fast",
                "litellm_params": {
                    "model": "gemini/gemini-2.0-flash",
                    "api_key": settings.GEMINI_API_KEY
                }
            })
            
        # Fallback to standard OpenAI if nothing else (or environment keys exist directly)
        if not model_list:
            # Add a mock indicator if no keys are found
            self.use_mock = True
            self.router = None
        else:
            self.use_mock = False
            self.router = Router(
                model_list=model_list,
                fallbacks=[{"nexus-fast": ["nexus-fast"]}],
                set_verbose=False,
                retry_after=3,
                num_retries=2
            )

    async def acompletion(self, model: str, messages: List[Dict[str, str]], agent_name: str = "unknown", **kwargs) -> Any:
        """Call LiteLLM Completion or fallback to Mock Completion if keys are missing.
        
        Args:
            model: The model alias (e.g., "nexus-fast")
            messages: Chat messages
            agent_name: Name of the calling agent (for metrics tracking)
        """
        start_time = time.monotonic()
        
        if self.use_mock:
            result = await self._mock_completion(model, messages, **kwargs)
            latency = int((time.monotonic() - start_time) * 1000)
            metrics_collector.record_call(
                model="mock", agent_name=agent_name,
                input_tokens=len(str(messages)) // 4,
                output_tokens=len(result.choices[0].message.content) // 4,
                latency_ms=latency, success=True,
            )
            return result
            
        try:
            # Enforce rate limiting based on model routing
            if "gemini" in getattr(self.router, "active_router", ""):
                response = await gemini_limiter.call(self.router.acompletion, model=model, messages=messages, **kwargs)
            else:
                response = await groq_limiter.call(self.router.acompletion, model=model, messages=messages, **kwargs)
            
            # Track token usage
            latency = int((time.monotonic() - start_time) * 1000)
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            
            actual_model = getattr(response, "model", model)
            metrics_collector.record_call(
                model=actual_model, agent_name=agent_name,
                input_tokens=input_tokens, output_tokens=output_tokens,
                latency_ms=latency, success=True,
            )
            
            return response
        except Exception as e:
            latency = int((time.monotonic() - start_time) * 1000)
            metrics_collector.record_call(
                model=model, agent_name=agent_name,
                latency_ms=latency, success=False,
            )
            
            # Check if mock fallback is allowed
            if not settings.ALLOW_MOCK_FALLBACK:
                raise RuntimeError(
                    f"LLM API failure: {str(e)}. "
                    f"Mock fallback is DISABLED (ALLOW_MOCK_FALLBACK=False). "
                    f"Fix your API keys or enable mock fallback for development."
                ) from e
            
            # Return mock completion if all upstream APIs fail
            print(f"LLM API failure: {str(e)}. Falling back to Mock Completion.")
            return await self._mock_completion(model, messages, **kwargs)

    async def astream_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Stream completion tokens."""
        if self.use_mock:
            mock_text = await self._get_mock_response_text(messages)
            for word in mock_text.split(" "):
                await asyncio.sleep(0.02)
                yield word + " "
            return

        try:
            response = await self.router.acompletion(model=model, messages=messages, stream=True, **kwargs)
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            if not settings.ALLOW_MOCK_FALLBACK:
                raise
            # Stream fallback mock
            mock_text = f"[LLM ERROR FALLBACK] {await self._get_mock_response_text(messages)}"
            for word in mock_text.split(" "):
                await asyncio.sleep(0.02)
                yield word + " "

    async def _mock_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Any:
        """Simulate LLM responses for development & testing."""
        await asyncio.sleep(0.5) # Simulate network latency
        text = await self._get_mock_response_text(messages)
        
        # Mimic LiteLLM response structure
        class Choices:
            def __init__(self, message_text):
                self.message = Message(message_text)
                
        class Message:
            def __init__(self, content):
                self.content = content
                
        class MockUsage:
            def __init__(self, prompt_tokens, completion_tokens):
                self.prompt_tokens = prompt_tokens
                self.completion_tokens = completion_tokens
                self.total_tokens = prompt_tokens + completion_tokens
                
        class MockResponse:
            def __init__(self, content, prompt_text):
                self.choices = [Choices(content)]
                self.model = "mock/llama-3.3-70b-mock"
                self.usage = MockUsage(
                    prompt_tokens=len(prompt_text) // 4,
                    completion_tokens=len(content) // 4,
                )
                
        prompt_text = str(messages)
        return MockResponse(text, prompt_text)

    async def _get_mock_response_text(self, messages: List[Dict[str, str]]) -> str:
        system_msg = messages[0].get("content", "") if messages else ""
        prompt = messages[-1].get("content", "").lower() if messages else ""
        
        # 0. Planner Agent Request — dynamic plan generation
        if "orchestration planner" in prompt or "available agents" in prompt:
            return json.dumps({
                "active_agents": [
                    "trigger_monitor", "company_enricher", "icp_matcher",
                    "shadow_agent", "persona_finder", "contact_enricher",
                    "summary_agent", "validator_agent"
                ],
                "reasoning": "Full pipeline activated for unknown company. All agents needed for comprehensive lead qualification.",
                "skip_reasons": {}
            })
            
        # ReAct Loop support
        if "To use a tool, reply EXACTLY with:" in system_msg:
            has_tool_result = any("TOOL_RESULT:" in m.get("content", "") for m in messages)
            if not has_tool_result:
                # First iteration: extract names from the user prompt
                # Parse the contact name from the prompt dynamically
                import re
                name_match = re.search(r'\"name\":\s*\"([^\"]+)\"', prompt)
                contact_name = name_match.group(1) if name_match else "Unknown Contact"
                company_match = re.search(r'at\s+([\w\s]+?):', prompt) or re.search(r'company[\"\s:]+([\w\s]+)', prompt)
                company_name = company_match.group(1).strip() if company_match else "Unknown Company"
                return f'TOOL: search_linkedin({{"name": "{contact_name}", "company": "{company_name}"}})'
            else:
                # Second iteration: parse contacts from the tool result and return as final answer
                tool_result_msg = [m.get("content", "") for m in messages if "TOOL_RESULT:" in m.get("content", "")]
                return f'FINAL_ANSWER: {tool_result_msg[-1].replace("TOOL_RESULT: ", "") if tool_result_msg else "[]"}'
        
        # 1. Shadow Agent Request
        if "shadow_agent" in prompt or "skeptical analyst" in prompt:
            confidence = random.randint(40, 75)
            if "razorx" in prompt:
                return '{"counter_argument": "RazorX Fintech is growing fast, but they only have 87 employees and are using Google Sheets. They might not be ready for enterprise-grade tooling, or they could build it themselves.", "risk_confidence": 65, "flaw_type": "readiness_risk"}'
            else:
                return '{"counter_argument": "The company may have raised capital, but their historical hiring rate shows a slow sales-cycle target list. High risk of long conversion delay.", "risk_confidence": 62, "flaw_type": "sales_cycle_risk"}'
                
        # 2. ICP Matcher Request
        if "icp score" in prompt or "ideal customer profile" in prompt:
            if "razorx" in prompt:
                return '{"score": 87, "justification": "RazorX matches all target criteria: Fintech sector, 87 employees (fits 20-500 bracket), and raised $15M Series A. Current tool is Google Sheets, indicating high urgency."}'
            if "acme" in prompt:
                return '{"score": 75, "justification": "AcmeCorp matches industry and employee count, but already uses BambooHR. Urgency is moderate."}'
            return '{"score": 45, "justification": "Company size or industry is outside the sweet spot, or they are experiencing a headcount reduction."}'

        # 3. Summary Agent Request
        if "actionable recommendation" in prompt or "outreach" in prompt:
            return "Based on the enrichment data, I recommend immediate outreach. Highlight how our HR platform automates onboarding for high-growth tech startups. The company shows strong growth signals and fits the primary SaaS targeting profiles."

        # 4. General fallback
        return "I have processed the request and verified the company information. The lead has high growth signals and fits the primary SaaS targeting profiles."

# Need json import for mock planner response
import json

llm_service = LLMService()
