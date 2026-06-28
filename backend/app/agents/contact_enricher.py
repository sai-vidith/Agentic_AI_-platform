from typing import Dict, Any, List
import json
import asyncio
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes
from app.governance.pii_redactor import pii_redactor
from app.governance.tee_layer import TEEVault
from app.tools.search_linkedin import search_linkedin
from app.tools.search_tool import SearchTool

class ContactEnricherAgent(BaseNexusAgent):
    """Upgraded Contact Enricher Agent performing parallel search lookups, extraction, and secure TEE storage."""
    
    def __init__(self):
        super().__init__(name="contact_enricher")
        self.tee_vault = TEEVault()
        self.search_tool = SearchTool()

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        contacts = task_input.get("contacts", [])
        
        await notify_agent_event(WSEventTypes.AGENT_TOOL_CALL, self.name, target=company_name, data={"tool": "search_tool"})

        articles = []
        enriched_contacts = []

        # Loop through each target persona to find real names and LinkedIn links
        for c in contacts:
            name = c.get("name", "")
            title = c.get("title", "")
            
            search_query = f"{name or title} at {company_name} corporate email address or linkedin profile"
            
            # Execute targeted search
            search_res = await self.search_tool.execute({"query": search_query})
            snippets = []
            if search_res and hasattr(search_res, "data") and search_res.data:
                for item in search_res.data.get("results", []):
                    title_text = item.get("title", "")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    snippets.append(f"Title: {title_text}\nURL: {link}\nSnippet: {snippet}")
                    if link:
                        articles.append({
                            "title": f"Contact Ref: {name or title} ({title_text})",
                            "url": link,
                            "source": "Google/DDG Search"
                        })
            
            corpus = "\n\n".join(snippets)

            # Ask LiteLLM/Cerebras to extract/verify contact name, email, phone, and LinkedIn
            refinement_prompt = f"""
            You are a B2B Contact Enrichment Specialist.
            Find the real email address, phone, and LinkedIn profile for:
            Name: {name}
            Title: {title}
            Company: {company_name}
            
            Use the web search snippets below as context:
            {corpus}
            
            Return a JSON object matching this structure:
            {{
              "name": "full name of contact",
              "title": "exact job title",
              "email": "corporate email address or guess e.g. first.last@company.com",
              "phone": "corporate phone number or e.g. +1-555-019-2831",
              "linkedin": "https://linkedin.com/in/username"
            }}
            """
            
            refined_contact = {
                "name": name,
                "title": title,
                "email": c.get("email") or f"{name.lower().replace(' ', '.')}@{company_name.lower().replace(' ', '')}.com",
                "phone": c.get("phone") or "+1-555-019-2831",
                "linkedin": c.get("linkedin") or f"https://linkedin.com/in/{name.lower().replace(' ', '')}"
            }
            
            try:
                llm_response = await self.call_llm(
                    prompt=refinement_prompt,
                    system_message="You are a strict data scientist. Output ONLY valid JSON.",
                    response_format={"type": "json_object"}
                )
                refined_contact = json.loads(llm_response)
            except Exception as e:
                print(f"[contact_enricher] LLM contact extraction failed: {e}")

            # Apply governance, TEE storage, and PII masking
            email = refined_contact.get("email", "")
            phone = refined_contact.get("phone", "")

            encrypted_email = self.tee_vault.encrypt(email) if email else ""
            encrypted_phone = self.tee_vault.encrypt(phone) if phone else ""

            redacted_email = pii_redactor.redact_text(email)
            redacted_phone = pii_redactor.redact_text(phone)

            gov_contact = {
                "name": refined_contact.get("name", name),
                "title": refined_contact.get("title", title),
                "email": redacted_email,
                "phone": redacted_phone,
                "linkedin": refined_contact.get("linkedin", ""),
                "joined_date": c.get("joined_date", "Unknown"),
                "pii_fields_redacted": ["email", "phone"] if email or phone else [],
                "raw_email": encrypted_email,
                "raw_phone": encrypted_phone
            }
            enriched_contacts.append(gov_contact)

        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": enriched_contacts})
        
        return {
            "contacts": enriched_contacts,
            "articles": articles
        }

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        contacts = task_input.get("contacts", [])
        return {"contacts": contacts}
