from typing import Dict, Any, List
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes
from app.governance.pii_redactor import pii_redactor
from app.governance.tee_layer import TEEVault

class ContactEnricherAgent(BaseNexusAgent):
    """Enriches contact details and applies secure TEE and PII governance checks."""
    
    def __init__(self):
        super().__init__(name="contact_enricher")
        self.tee_vault = TEEVault()

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        contacts = task_input.get("contacts", [])
        
        governed_contacts = []
        for c in contacts:
            email = c.get("email", "")
            phone = c.get("phone", "")
            
            # Enforce Governance & Safety:
            # 1. Encrypt and store raw PII in TEE Vault
            encrypted_email = self.tee_vault.encrypt(email) if email else ""
            encrypted_phone = self.tee_vault.encrypt(phone) if phone else ""
            
            # 2. Redact/mask PII in user-facing fields
            redacted_email = pii_redactor.redact_text(email)
            redacted_phone = pii_redactor.redact_text(phone)
            
            gov_contact = {
                "name": c.get("name", ""),
                "title": c.get("title", ""),
                "email": redacted_email,
                "phone": redacted_phone,
                "linkedin": c.get("linkedin", ""),
                "joined_date": c.get("joined_date"),
                "pii_fields_redacted": ["email", "phone"] if email or phone else [],
                "raw_email": encrypted_email,
                "raw_phone": encrypted_phone
            }
            governed_contacts.append(gov_contact)

        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": governed_contacts})
        return {"contacts": governed_contacts}

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        contacts = task_input.get("contacts", [])
        return {"contacts": contacts}
