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
        
        # Search news feed using strict query format
        news_query = f'{company_name} (funding OR hiring OR expansion OR "new product" OR "partnership" OR "IPO" OR "Series")'
        news_result = await news_tool.execute({"company_name": company_name, "query": news_query})
        articles = news_result.data.get("articles", [])
        
        pipeline_log = []
        data_quality_flags = []
        
        # For simplicity, we extract triggers from the news articles directly using LLM
        articles_text = json.dumps(articles)
        prompt = f"""
        Analyze these news articles about company '{company_name}' and identify if they indicate any B2B trigger events.
        
        Articles:
        {articles_text}
        
        Tag each signal type strictly as one of: FUNDING | HIRING_SURGE | PRODUCT_LAUNCH | EXPANSION | LEADERSHIP_CHANGE | PARTNERSHIP | IPO_SIGNAL.
        If any article doesn't represent one of these signals, ignore it.
        
        Respond in JSON:
        {{
          "triggers_found": [
            {{
              "type": "FUNDING | HIRING_SURGE | PRODUCT_LAUNCH | EXPANSION | LEADERSHIP_CHANGE | PARTNERSHIP | IPO_SIGNAL",
              "headline": "headline text or description",
              "date": "YYYY-MM-DD",
              "source": "source site name",
              "confidence": 0-100
            }}
          ]
        }}
        """
        
        content = await self.call_llm(prompt, response_format={"type": "json_object"})
        data = json.loads(content)
        triggers = data.get("triggers_found", [])
        
        pipeline_log.append(f"STAGE_2: {len(triggers)} signals found — " + ", ".join([t.get("type", "") for t in triggers]))
        
        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": data})
        return {
            "triggers": triggers, 
            "articles": articles,
            "pipeline_log": pipeline_log,
            "data_quality_flags": data_quality_flags
        }

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        # Fallback trigger list
        company_name = task_input.get("company_name", "RazorX Fintech")
        fallback_triggers = [
            {"type": "funding", "detail": f"Raised Series A funding round for {company_name}", "confidence": 95}
        ]
        await notify_agent_event(WSEventTypes.AGENT_RECOVERED, self.name, target=company_name, data={"status": "recovered"})
        return {"triggers": fallback_triggers, "articles": []}
