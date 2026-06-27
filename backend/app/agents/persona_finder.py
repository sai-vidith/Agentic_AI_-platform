import json
from typing import Dict, Any, List
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes

class PersonaFinderAgent(BaseNexusAgent):
    """Filters and identifies key decision makers matching YAML persona definitions."""
    
    def __init__(self):
        super().__init__(name="persona_finder")

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        raw_contacts = task_input.get("raw_enrichment_data", {}).get("contacts", [])
        persona_rules = task_input.get("persona_rules", {})
        
        prompt = f"""
        Filter the following contacts list to find the best decision maker matching these persona guidelines.
        
        Guidelines:
        {json.dumps(persona_rules)}
        
        Contacts list:
        {json.dumps(raw_contacts)}
        
        Return the matched decision makers, sorted by priority.
        Format strictly as JSON:
        {{
          "matched_contacts": [
            {{
              "name": "Full Name",
              "title": "Exact Title",
              "email": "email_address",
              "phone": "phone_number",
              "linkedin": "linkedin_profile_url",
              "joined_date": "YYYY-MM-DD",
              "persona_rank": 1
            }}
          ]
        }}
        """
        
        content = await self.call_llm(prompt, response_format={"type": "json_object"})
        data = json.loads(content)
        
        matched = data.get("matched_contacts", [])
        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": matched})
        return {"contacts": matched}

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        fallback_contacts = [
            {
                "name": "Priya Sharma",
                "title": "Head of People Operations",
                "email": "priya.sharma@razorx.in",
                "phone": "+91-9876543210",
                "linkedin": "linkedin.com/in/priya-sharma-razorx",
                "persona_rank": 1
            }
        ]
        return {"contacts": fallback_contacts}
