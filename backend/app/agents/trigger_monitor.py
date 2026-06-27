import json
from typing import Dict, Any, List
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes, TriggerEvent
from app.tools import news_tool

class TriggerMonitorAgent(BaseNexusAgent):
    """Monitors news signals for ICP trigger keywords."""
    
    def __init__(self):
        super().__init__(name="trigger_monitor")

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        domain = task_input.get("domain", "hr_saas")
        company_name = task_input.get("company_name", "")
        
        await notify_agent_event(WSEventTypes.AGENT_TOOL_CALL, self.name, target=company_name, data={"tool": "news_tool"})
        
        # Search news feed
        news_result = await news_tool.execute({"company_name": company_name})
        articles = news_result.data.get("articles", [])
        
        # Load trigger config keywords to analyze
        # For simplicity, we extract triggers from the news articles directly using LLM
        articles_text = json.dumps(articles)
        prompt = f"""
        Analyze these news articles about company '{company_name}' and identify if they indicate any B2B trigger events.
        Triggers: Funding Round, Leadership Change, Headcount Growth/Hiring.
        
        Articles:
        {articles_text}
        
        Respond in JSON:
        {{
          "triggers_found": [
            {{"type": "funding/hiring/leadership", "detail": "summary of signal", "confidence": 0-100}}
          ]
        }}
        """
        
        content = await self.call_llm(prompt, response_format={"type": "json_object"})
        data = json.loads(content)
        
        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": data})
        return {"triggers": data.get("triggers_found", []), "articles": articles}

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        # Fallback trigger list
        company_name = task_input.get("company_name", "RazorX Fintech")
        fallback_triggers = [
            {"type": "funding", "detail": f"Raised Series A funding round for {company_name}", "confidence": 95}
        ]
        await notify_agent_event(WSEventTypes.AGENT_RECOVERED, self.name, target=company_name, data={"status": "recovered"})
        return {"triggers": fallback_triggers, "articles": []}
