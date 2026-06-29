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
    # Exclude known invalid/expired Gemini keys
    if "aq.ab8rn6lezic" in key_lower or "aizasyasz4ab" in key_lower:
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
        
        # Clean quotes from environment inputs (Pydantic keeps literal quotes if present in .env)
        openai_key = (settings.OPENAI_API_KEY or "").strip('"\'')
        openai_base = (settings.OPENAI_API_BASE or "").strip('"\'')
        groq_key = (settings.GROQ_API_KEY or "").strip('"\'')
        gemini_key = (settings.GEMINI_API_KEY or "").strip('"\'')

        # GitHub Models (OpenAI Compatible)
        if openai_key and openai_key.startswith("github_pat"):
            model_list.append({
                "model_name": "nexus-fast",
                "litellm_params": {
                    "model": "openai/gpt-4o",
                    "api_key": openai_key,
                    "api_base": openai_base
                }
            })
            # Add GPT-4o-mini as a fallback for nexus-fast if GPT-4o hits rate limits
            model_list.append({
                "model_name": "nexus-fast",
                "litellm_params": {
                    "model": "openai/gpt-4o-mini",
                    "api_key": openai_key,
                    "api_base": openai_base
                }
            })
            model_list.append({
                "model_name": "nexus-shadow",
                "litellm_params": {
                    "model": "openai/gpt-4o-mini",
                    "api_key": openai_key,
                    "api_base": openai_base
                }
            })
        
        # Groq
        if is_real_key(groq_key, "groq"):
            model_list.append({
                "model_name": "nexus-fast",
                "litellm_params": {
                    "model": "groq/llama-3.3-70b-versatile",
                    "api_key": groq_key
                }
            })
            model_list.append({
                "model_name": "nexus-fast",
                "litellm_params": {
                    "model": "groq/llama-3.1-8b-instant",
                    "api_key": groq_key
                }
            })
            model_list.append({
                "model_name": "nexus-shadow",
                "litellm_params": {
                    "model": "groq/llama-3.1-8b-instant",
                    "api_key": groq_key
                }
            })
            
        # Gemini
        if is_real_key(gemini_key, "gemini"):
            model_list.append({
                "model_name": "nexus-fast",
                "litellm_params": {
                    "model": "gemini/gemini-2.0-flash",
                    "api_key": gemini_key
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
        
        # Helper: Extract company name if possible
        import re
        company_name = "Target Company"
        comp_match = re.search(r"company\s+'?\"?([a-zA-Z0-9\s\.\-_]+)'?\"?", prompt)
        if comp_match:
            company_name = comp_match.group(1).strip()
        else:
            comp_match_for = re.search(r"for\s+'?\"?([a-zA-Z0-9\s\.\-_]+)'?\"?", prompt)
            if comp_match_for:
                company_name = comp_match_for.group(1).strip()

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

        # 1. Company Extraction / Startup Discovery
        if "search results about" in prompt and "companies" in prompt:
            if "cybersecurity" in prompt or "cyber" in prompt:
                companies = ["Securden", "Wiz", "Armis", "Snyk", "SentinelOne"]
            else:
                companies = ["Keka HR", "Darwinbox", "Rippling", "Deel", "Gusto"]
            return json.dumps({"companies": companies})

        # 2. Trigger Monitor Agent
        if "b2b trigger events" in prompt or "triggers_found" in prompt:
            return json.dumps({
                "triggers_found": [
                    {"type": "funding", "detail": f"Recently raised Series B funding round for {company_name}", "confidence": 95},
                    {"type": "hiring", "detail": f"Active job openings for security/HR administrators at {company_name}", "confidence": 88}
                ]
            })

        # 3. Company Enricher Agent
        if "enrichment specialist" in prompt or ("website" in prompt and "founded" in prompt and "hq" in prompt):
            is_cyber = "cybersecurity" in prompt or "cyber" in prompt or "securden" in prompt or "wiz" in prompt or "armis" in prompt or "snyk" in prompt
            return json.dumps({
                "name": company_name,
                "industry": "Cybersecurity Tools" if is_cyber else "HR SaaS / Fintech",
                "employees": 180,
                "founded": 2020,
                "hq": "Chennai, India" if is_cyber else "Bengaluru, India",
                "tech_stack": ["React", "AWS", "Python", "Docker"] if is_cyber else ["Node.js", "React", "PostgreSQL"],
                "current_hr_tool": "Excel" if is_cyber else "Gusto",
                "recent_funding": {
                    "round": "Series A",
                    "amount_usd": 15000000,
                    "date": "2025-10-10"
                },
                "growth_rate": "40% headcount growth",
                "website": f"https://www.{company_name.lower().replace(' ', '')}.com",
                "linkedin": f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '')}",
                "description": f"{company_name} is a leading provider of software solutions catering to enterprise accounts globally."
            })

        # 4. ICP Matcher Agent
        if "icp score" in prompt or "ideal customer profile" in prompt:
            return json.dumps({
                "industry_score": 90,
                "scale_score": 85,
                "intent_score": 95,
                "tech_score": 80,
                "score": 88,
                "justification": f"{company_name} matches all core Ideal Customer Profile metrics including industry vertical alignment, growth signals, and scaling headcount."
            })

        # 5. Shadow Agent Critique / Debate (Advocate & Critique)
        if "shadow_agent" in prompt or "skeptical analyst" in prompt:
            return json.dumps({
                "counter_argument": f"{company_name} has strong momentum, but faces local domestic competition and could build features in-house.",
                "reasons": [
                    "Strong local competition in target geography",
                    "In-house technical capabilities might lead them to build rather than buy",
                    "Current sales cycles for their customer base are relatively long"
                ],
                "risk_confidence": 60,
                "flaw_type": "competition_risk"
            })

        # 6. Persona Finder Agent / Matched Contacts
        if "matched_contacts" in prompt:
            is_cyber = "cybersecurity" in prompt or "cyber" in prompt or "ciso" in prompt or "cto" in prompt
            if is_cyber:
                contacts = [
                    {
                        "name": "Curtis Simpson",
                        "title": "Chief Information Security Officer",
                        "email": f"curtis.simpson@{company_name.lower().replace(' ', '')}.com",
                        "phone": "+91-98401-23456",
                        "linkedin": f"https://linkedin.com/in/curtissimpson-{company_name.lower().replace(' ', '')}",
                        "joined_date": "2023-01-10",
                        "persona_rank": 1
                    },
                    {
                        "name": "Nadir Izrael",
                        "title": "Chief Technology Officer",
                        "email": f"nadir.izrael@{company_name.lower().replace(' ', '')}.com",
                        "phone": "+91-98401-23457",
                        "linkedin": f"https://linkedin.com/in/nadirizrael-{company_name.lower().replace(' ', '')}",
                        "joined_date": "2021-06-15",
                        "persona_rank": 2
                    }
                ]
            else:
                contacts = [
                    {
                        "name": "Sarah Jenkins",
                        "title": "VP of People Operations",
                        "email": f"sarah.jenkins@{company_name.lower().replace(' ', '')}.com",
                        "phone": "+91-80560-12345",
                        "linkedin": f"https://linkedin.com/in/sarahjenkins-people-{company_name.lower().replace(' ', '')}",
                        "joined_date": "2022-09-01",
                        "persona_rank": 1
                    },
                    {
                        "name": "Rahul Kumar",
                        "title": "Head of Human Resources",
                        "email": f"rahul.kumar@{company_name.lower().replace(' ', '')}.com",
                        "phone": "+91-80560-12346",
                        "linkedin": f"https://linkedin.com/in/rahulkumar-hr-{company_name.lower().replace(' ', '')}",
                        "joined_date": "2023-03-20",
                        "persona_rank": 2
                    }
                ]
            return json.dumps({"matched_contacts": contacts})
            
        # ReAct Loop support
        if "To use a tool, reply EXACTLY with:" in system_msg:
            has_tool_result = any("TOOL_RESULT:" in m.get("content", "") for m in messages)
            if not has_tool_result:
                name_match = re.search(r'\"name\":\s*\"([^\"]+)\"', prompt)
                contact_name = name_match.group(1) if name_match else "Unknown Contact"
                return f'TOOL: search_linkedin({{"name": "{contact_name}", "company": "{company_name}"}})'
            else:
                tool_result_msg = [m.get("content", "") for m in messages if "TOOL_RESULT:" in m.get("content", "")]
                return f'FINAL_ANSWER: {tool_result_msg[-1].replace("TOOL_RESULT: ", "") if tool_result_msg else "[]"}'

        # Debate Adjudication
        if "status" in prompt and "confirmed" in prompt and "divergence_warning" in prompt:
            return json.dumps({
                "status": "CONFIRMED",
                "reason": f"Advocate successfully resolved compliance checks for {company_name}.",
                "reasons": ["Fit is strong, no critical blocker."],
                "confidence": 85,
                "force_human_review": False
            })

        # 7. Actionable Outreach recommendation / Summary Agent Request
        if "actionable recommendation" in prompt or "outreach" in prompt:
            return f"Subject: Transforming Outreach for {company_name}\n\nHi Sarah,\n\nI noticed {company_name} is scaling operations post your Series A round. Our platform is designed to automate compliance checks and streamline workflows, which aligns with your current stack."

        # 8. General fallback
        return f"I have processed the request and verified the company information for {company_name}. The lead has high growth signals and fits the primary SaaS targeting profiles."

# Need json import for mock planner response
import json

llm_service = LLMService()
