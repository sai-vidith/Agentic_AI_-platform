from typing import Dict, Any
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes
from app.tools import enrichment_tool

class CompanyEnricherAgent(BaseNexusAgent):
    """Enriches company metadata using enrichment tools."""
    
    def __init__(self):
        super().__init__(name="company_enricher")

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        
        await notify_agent_event(WSEventTypes.AGENT_TOOL_CALL, self.name, target=company_name, data={"tool": "enrichment_tool"})
        
        enrich_result = await enrichment_tool.execute({"company_name": company_name})
        data = enrich_result.data
        
        company_details = data.get("company", {})
        
        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": company_details})
        return {
            "company_details": company_details,
            "raw_enrichment_data": data
        }

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "RazorX Fintech")
        fallback_details = {
            "name": company_name,
            "industry": "Software",
            "employees": 100,
            "founded": 2021,
            "hq": "Unknown",
            "tech_stack": ["React", "Node.js"],
            "current_hr_tool": "Excel",
            "recent_funding": {"round": "Series A", "amount_usd": 10000000},
            "growth_rate": "Moderate"
        }
        return {
            "company_details": fallback_details,
            "raw_enrichment_data": {}
        }
