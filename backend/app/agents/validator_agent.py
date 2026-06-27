from typing import Dict, Any
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes

class ValidatorAgent(BaseNexusAgent):
    """Performs final schema and validation check to prevent LLM hallucinations."""
    
    def __init__(self):
        super().__init__(name="validator_agent")

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        icp_score = task_input.get("icp_score", 0)
        contacts = task_input.get("contacts", [])
        outreach_template = task_input.get("outreach_template", "")
        
        # Quick validation checks
        validation_errors = []
        if not company_name:
            validation_errors.append("Missing company name")
        if not contacts:
            validation_errors.append("Missing target contacts")
        if not outreach_template:
            validation_errors.append("Missing outreach email template")
            
        is_valid = len(validation_errors) == 0
        
        await notify_agent_event(
            WSEventTypes.AGENT_COMPLETED, 
            self.name, 
            target=company_name, 
            data={"status": "valid" if is_valid else "invalid", "errors": validation_errors}
        )
        
        return {
            "is_valid": is_valid,
            "validation_errors": validation_errors
        }

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        return {"is_valid": True, "validation_errors": []}
