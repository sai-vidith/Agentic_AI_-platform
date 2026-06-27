import json
from typing import Dict, Any
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes

class SummaryAgent(BaseNexusAgent):
    """Compiles enriched lead data and writes tailored outreach messaging."""
    
    def __init__(self):
        super().__init__(name="summary_agent")

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_details = task_input.get("company_details", {})
        company_name = company_details.get("name", "")
        contacts = task_input.get("contacts", [])
        icp_score = task_input.get("icp_score", 0)
        triggers = task_input.get("triggers", [])
        
        primary_contact = contacts[0] if contacts else {}
        
        prompt = f"""
        Draft a personalized outreach email to the primary decision maker at this company.
        
        Company Profile:
        {json.dumps(company_details)}
        
        Primary Contact:
        {json.dumps(primary_contact)}
        
        Triggers Spotted:
        {json.dumps(triggers)}
        
        ICP Compatibility Score: {icp_score}/100
        
        Write a concise, compelling message referencing recent funding/hiring triggers and their current tool stack.
        Respond as JSON:
        {{
          "outreach_template": "Subject: ...\\n\\nBody: ...",
          "evidence_chain": [
            "Signal 1: Raised Series A round.",
            "Signal 2: Headcount growing rapidly."
          ]
        }}
        """
        
        content = await self.call_llm(prompt, response_format={"type": "json_object"})
        data = json.loads(content)
        
        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": data})
        return {
            "outreach_template": data.get("outreach_template", ""),
            "evidence_chain": data.get("evidence_chain", [])
        }

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "Unknown Company")
        contacts = task_input.get("contacts", [])
        contact_name = contacts[0].get("name", "Hiring Manager") if contacts else "Hiring Manager"
        return {
            "outreach_template": f"Subject: Managing growth at {company_name}\n\nHi {contact_name},\n\nCongrats on the recent funding news! I noticed you are expanding the team and wanted to reach out regarding our HR scaling platform...",
            "evidence_chain": ["Signal: Recent Series A funding announcement."]
        }
