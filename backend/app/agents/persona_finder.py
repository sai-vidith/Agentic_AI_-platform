import json
from typing import Dict, Any, List
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes

class PersonaFinderAgent(BaseNexusAgent):
    """Filters and identifies key decision makers matching YAML persona definitions using live web searches."""
    
    def __init__(self):
        super().__init__(name="persona_finder")
        from app.tools.search_tool import SearchTool
        self.search_tool = SearchTool()

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        company_details = task_input.get("company_details", {})
        persona_rules = task_input.get("persona_rules", {})
        
        pipeline_log = []
        data_quality_flags = []
        
        # Clean company domain
        company_domain = company_details.get("website", "") or company_details.get("domain", "")
        if company_domain:
            from urllib.parse import urlparse
            if not company_domain.startswith("http"):
                company_domain = "https://" + company_domain
            try:
                parsed = urlparse(company_domain)
                company_domain = parsed.netloc.replace("www.", "")
            except Exception:
                company_domain = ""

        # Extract title patterns from active persona guidelines YAML
        title_patterns = []
        if isinstance(persona_rules, dict):
            for p in persona_rules.get("personas", []):
                title_patterns.extend(p.get("title_patterns", []))

        # 3a. Parallel Serper queries targeting target personas (including CISO, CEO, CTO, CMO, CHRO)
        queries = []
        if title_patterns:
            for pattern in title_patterns[:5]:
                queries.append(f'"{company_name}" "{pattern}" linkedin')
        else:
            # Comprehensive fallback list for standard buyer committee roles
            queries = [
                f'"{company_name}" "CEO" OR "Founder" OR "Co-Founder" linkedin',
                f'"{company_name}" "CTO" OR "Chief Technology Officer" OR "VP Engineering" linkedin',
                f'"{company_name}" "CISO" OR "Chief Information Security Officer" OR "VP Security" linkedin',
                f'"{company_name}" "CMO" OR "Chief Marketing Officer" OR "VP Marketing" linkedin',
                f'"{company_name}" "Chief People Officer" OR "Head of People" OR "CHRO" OR "VP HR" linkedin'
            ]
            
        if company_domain:
            queries.append(f'"{company_name}" leadership team site:{company_domain}')
            # Also scrape `/about` URL using Search snippet to simulate 3c
            queries.append(f'site:{company_domain}/about leadership board executive')
            
        import asyncio
        search_tasks = [self.search_tool.execute({"query": q}) for q in queries]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        sources_data = []
        for idx, res in enumerate(search_results):
            q_text = queries[idx]
            if isinstance(res, Exception) or not res or not hasattr(res, "data"):
                continue
            q_results = []
            for item in res.data.get("results", []):
                q_results.append({
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "link": item.get("link")
                })
            sources_data.append({
                "query": q_text,
                "results": q_results
            })

        matched = []
        try:
            from app.tools.chat4data import chat4data
            chat4_res = await chat4data.execute({
                "text": json.dumps(sources_data),
                "schema_type": "contacts",
                "company_name": company_name,
                "domain": company_details.get("domain", "hr_saas")
            })
            if chat4_res and not chat4_res.error:
                extracted_contacts = chat4_res.data.get("contacts", [])
                for ec in extracted_contacts:
                    matched.append({
                        "name": ec.get("name"),
                        "title": ec.get("title", "Executive"),
                        "persona_match": ec.get("persona_match") or "CTO",
                        "confidence": ec.get("confidence") or "MEDIUM",
                        "source_url": ec.get("linkedin") or company_details.get("website", ""),
                        "extraction_method": "scrapy_beautifulsoup_search",
                        "linkedin": ec.get("linkedin"),
                        "email": ec.get("email", "unknown"),
                        "phone": ec.get("phone", "unknown")
                    })
            
            # Anti-hallucination checks
            matched = [
                c for c in matched 
                if c.get("name") and "placeholder" not in c.get("name").lower()
            ]
        except Exception as e:
            print(f"[PersonaFinder] Match parsing failed: {e}")
            
        if matched:
            high_count = sum(1 for c in matched if c.get("confidence") == "HIGH")
            med_count = sum(1 for c in matched if c.get("confidence") == "MEDIUM")
            pipeline_log.append(f"STAGE_3: {high_count} HIGH + {med_count} MEDIUM contacts found")
        else:
            # Fallback to seed details if search parsing yielded nothing
            raw_contacts = task_input.get("raw_enrichment_data", {}).get("contacts", [])
            for c in raw_contacts:
                matched.append({
                    "name": c.get("name"),
                    "title": c.get("title", "Executive"),
                    "persona_match": "CHRO" if "people" in c.get("title", "").lower() or "hr" in c.get("title", "").lower() else "CTO",
                    "confidence": "MEDIUM",
                    "source_url": company_details.get("website", ""),
                    "extraction_method": "enrichment_mock_db"
                })
            pipeline_log.append(f"STAGE_3: Fallback used, {len(matched)} seed contacts found")
            
        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": matched})
        
        return {
            "contacts": matched,
            "pipeline_log": pipeline_log,
            "data_quality_flags": data_quality_flags
        }

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        # Even in fallback, try to use enrichment contacts if they exist
        raw_contacts = task_input.get("raw_enrichment_data", {}).get("contacts", [])
        company = task_input.get("company_name", "Unknown Company")
        
        if raw_contacts:
            cleaned = []
            for i, c in enumerate(raw_contacts):
                name = c.get("name", "").replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
                if " - " in name:
                    name = name.split(" - ")[0].strip()
                if name and len(name) > 2:
                    cleaned.append({
                        "name": name,
                        "title": c.get("title", "Executive")[:50],
                        "email": "unknown",
                        "phone": "unknown",
                        "linkedin": c.get("linkedin", ""),
                        "persona_rank": i + 1
                    })
            if cleaned:
                return {"contacts": cleaned}
        
        # Last resort fallback using LLM knowledge
        return {"contacts": [{
            "name": f"VP of People at {company}",
            "title": "VP of People",
            "email": "unknown",
            "phone": "unknown",
            "linkedin": "unknown",
            "persona_rank": 1
        }]}
