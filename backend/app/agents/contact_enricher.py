from typing import Dict, Any, List
import json
import asyncio
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes
from app.governance.pii_redactor import pii_redactor
from app.governance.tee_layer import TEEVault
from app.tools.search_linkedin import search_linkedin
from app.tools.search_tool import SearchTool
from app.agents.enrichment_utils import dedupe_contacts, extract_domain, normalize_contact

class ContactEnricherAgent(BaseNexusAgent):
    """Upgraded Contact Enricher Agent performing parallel search lookups, extraction, and secure TEE storage."""
    
    def __init__(self):
        super().__init__(name="contact_enricher")
        self.tee_vault = TEEVault()
        self.search_tool = SearchTool()

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        contacts = task_input.get("contacts", [])
        company_details = task_input.get("company_details", {})
        
        await notify_agent_event(WSEventTypes.AGENT_TOOL_CALL, self.name, target=company_name, data={"tool": "search_tool"})

        pipeline_log = []
        data_quality_flags = []
        articles = []
        
        # Clean company domain
        company_domain = extract_domain(company_details.get("website", "") or company_details.get("domain", ""))

        # Run global company queries in parallel (email pattern + phone)
        import asyncio
        global_tasks = [
            self.search_tool.execute({"query": f'"{company_name}" contact phone number press release'})
        ]
        if company_domain:
            global_tasks.append(self.search_tool.execute({"query": f'"{company_name}" email "@{company_domain}" contact'}))
            
        global_results = await asyncio.gather(*global_tasks, return_exceptions=True)
        
        phone_res = global_results[0]
        pattern_res = global_results[1] if len(global_results) > 1 else None

        # --- STAGE 4a: EMAIL PATTERN INFERENCE ---
        email_pattern = None
        if pattern_res and not isinstance(pattern_res, Exception) and hasattr(pattern_res, "data"):
            results = pattern_res.data.get("results", [])
            import re
            found_emails = []
            for item in results:
                snippet = item.get("snippet", "")
                emails = re.findall(r"([a-zA-Z0-9\.\-\_]+@" + re.escape(company_domain) + ")", snippet, re.IGNORECASE)
                if emails:
                    found_emails.extend(emails)
            
            if found_emails:
                sample_email = found_emails[0].split("@")[0].lower()
                if "." in sample_email:
                    email_pattern = "first.last"
                elif "_" in sample_email:
                    email_pattern = "first_last"
                else:
                    email_pattern = "first"
                pipeline_log.append(f"STAGE_4: email pattern inferred â†’ {email_pattern}@{company_domain}")

        # Parse global company phone
        phone_to_store = None
        if phone_res and not isinstance(phone_res, Exception) and hasattr(phone_res, "data"):
            ph_results = phone_res.data.get("results", [])
            for item in ph_results:
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                if company_domain and company_domain in link:
                    import re
                    phones = re.findall(r"(\+?[0-9]{1,3}[ \-\.]?\(?[0-9]{2,4}\)?[ \-\.]?[0-9]{3,4}[ \-\.]?[0-9]{3,4})", snippet)
                    if phones:
                        phone_to_store = phones[0]
                        break

        # Define individual contact lookup helper
        async def enrich_single_contact(c):
            name = c.get("name", "") or c.get("full_name", "")
            title = c.get("title", "")
            linkedin_url = c.get("linkedin_url") or c.get("linkedin")
            
            # 4c. Validate/resolve personal LinkedIn profile URL
            resolved_li = None
            if linkedin_url and "linkedin.com/in/" in linkedin_url.lower():
                import re
                match = re.search(r"linkedin\.com/in/([a-z0-9\-]+)", linkedin_url.lower())
                if match:
                    slug = match.group(1).strip("/")
                    if slug not in ("unavailable", "search", "login", "jobs", "pub"):
                        resolved_li = f"https://www.linkedin.com/in/{slug}"
            
            # Run contact-specific lookup tasks in parallel
            tasks = [self.search_tool.execute({"query": f'"{name}" "{company_name}" email contact'})]
            has_li_search = False
            if not resolved_li and name:
                tasks.append(self.search_tool.execute({"query": f'"{name}" "{company_name}" site:linkedin.com/in'}))
                has_li_search = True
                
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            person_email_res = task_results[0]
            li_res = task_results[1] if has_li_search else None
            
            # Parse LinkedIn search results if resolved_li is still None
            if not resolved_li and li_res and not isinstance(li_res, Exception) and hasattr(li_res, "data"):
                li_results = li_res.data.get("results", [])
                for item in li_results:
                    link = item.get("link", "")
                    import re
                    match = re.search(r"linkedin\.com/in/([a-z0-9\-]+)", link.lower())
                    if match:
                        slug = match.group(1).strip("/")
                        if slug not in ("unavailable", "search", "login", "jobs", "pub"):
                            resolved_li = f"https://www.linkedin.com/in/{slug}"
                            break
                            
            if not resolved_li:
                data_quality_flags.append(f"LINKEDIN_UNRESOLVED: {name}")

            # 4a. Find exact email or infer pattern
            exact_email = None
            email_confidence = None
            
            if person_email_res and not isinstance(person_email_res, Exception) and hasattr(person_email_res, "data"):
                pe_results = person_email_res.data.get("results", [])
                for item in pe_results:
                    snippet = item.get("snippet", "")
                    if company_domain:
                        import re
                        emails = re.findall(r"([a-zA-Z0-9\.\-\_]+@" + re.escape(company_domain) + ")", snippet, re.IGNORECASE)
                        if emails:
                            exact_email = emails[0].lower()
                            email_confidence = "HIGH"
                            break
                            
            email_to_store = None
            if exact_email:
                email_to_store = exact_email
            elif email_pattern and company_domain and name:
                parts = name.lower().split()
                first = parts[0] if len(parts) > 0 else ""
                last = parts[-1] if len(parts) > 1 else ""
                if email_pattern == "first.last" and first and last:
                    email_to_store = f"{first}.{last}@{company_domain}"
                elif email_pattern == "first_last" and first and last:
                    email_to_store = f"{first}_{last}@{company_domain}"
                else:
                    email_to_store = f"{first}@{company_domain}"
                email_confidence = "MEDIUM"
                data_quality_flags.append(f"PATTERN_EMAIL: email inferred from domain pattern for {name}")
            else:
                email_confidence = None

            if not phone_to_store:
                data_quality_flags.append(f"PARTIAL_ENRICHMENT: phone not found for {name}")

            # Apply TEE encryption and PII redacting
            encrypted_email = self.tee_vault.encrypt(email_to_store) if email_to_store else ""
            encrypted_phone = self.tee_vault.encrypt(phone_to_store) if phone_to_store else ""

            redacted_email = pii_redactor.redact_text(email_to_store) if email_to_store else None
            redacted_phone = pii_redactor.redact_text(phone_to_store) if phone_to_store else None

            return normalize_contact({
                "name": name,
                "full_name": name,
                "title": title,
                "persona_match": c.get("persona_match") or ("CHRO" if "people" in title.lower() or "hr" in title.lower() else "CTO"),
                "email": redacted_email,
                "email_confidence": email_confidence,
                "phone": redacted_phone,
                "linkedin": resolved_li,
                "linkedin_url": resolved_li,
                "source_url": c.get("source_url") or company_details.get("website", ""),
                "confidence": c.get("confidence") or "MEDIUM",
                "extraction_method": c.get("extraction_method") or "serper_snippet",
                "pii_fields_redacted": ["email", "phone"] if email_to_store or phone_to_store else [],
                "raw_email": encrypted_email,
                "raw_phone": encrypted_phone
            }, default_source_url=company_details.get("website", ""))

        # Run contact enrichment for all contacts in parallel
        enrich_tasks = [enrich_single_contact(c) for c in contacts]
        enriched_results = await asyncio.gather(*enrich_tasks, return_exceptions=True)
        enriched_contacts = [
            c for c in enriched_results
            if isinstance(c, dict) and (c.get("name") or c.get("full_name"))
        ]
        enriched_contacts = dedupe_contacts(enriched_contacts, default_source_url=company_details.get("website", ""))
        
        pipeline_log.append(f"STAGE_4: {sum(1 for c in enriched_contacts if c.get('email'))} email confirmed/inferred, phone extraction processed")

        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": enriched_contacts})
        
        return {
            "contacts": enriched_contacts,
            "articles": articles,
            "pipeline_log": pipeline_log,
            "data_quality_flags": data_quality_flags
        }

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        contacts = task_input.get("contacts", [])
        return {"contacts": dedupe_contacts(contacts)}



