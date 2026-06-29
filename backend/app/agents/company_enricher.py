from typing import Dict, Any, List
import json
import asyncio
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes
from app.tools.search_tool import SearchTool
from app.tools.enrichment_tool import EnrichmentTool

class CompanyEnricherAgent(BaseNexusAgent):
    """Refined Company Enricher Agent using intensive multi-source search and LLM extraction."""
    
    def __init__(self):
        super().__init__(name="company_enricher")
        self.search_tool = SearchTool()
        self.enrichment_tool = EnrichmentTool()

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_name = task_input.get("company_name", "")
        if not company_name:
            return {"company_details": {}, "raw_enrichment_data": {}, "pipeline_log": [], "data_quality_flags": []}

        pipeline_log = []
        data_quality_flags = []

        await notify_agent_event(WSEventTypes.AGENT_TOOL_CALL, self.name, target=company_name, data={"tool": "search_tool"})

        # Helpers
        def get_domain(url: str) -> str:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(url)
                return parsed.netloc.lower()
            except Exception:
                return ""

        def is_aggregator(url: str) -> bool:
            aggregators = [
                "globaldata", "zoominfo", "apollo.io", "crunchbase", "dnb.com",
                "pitchbook", "owler", "rocketreach", "lusha", "clearbit",
                "linkedin.com/company", "similarweb", "datanyze"
            ]
            domain = get_domain(url)
            return any(agg in domain or agg in url.lower() for agg in aggregators)

        def is_path_shallow(url: str) -> bool:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(url)
                path = parsed.path.strip("/")
                return path in ("", "about", "home", "about-us", "contact")
            except Exception:
                return False

        # --- Parallel execution of all searches & database lookup (Latency Optimization) ---
        queries = [
            f'"{company_name}" official website',
            f'"{company_name}" site:linkedin.com/company',
            f'"{company_name}" headcount growth 2024 OR 2025',
            f"{company_name} company overview website industry head office",
            f"{company_name} funding rounds tech stack tools"
        ]
        
        import asyncio
        tasks = [self.search_tool.execute({"query": q}) for q in queries] + [self.enrichment_tool.execute({"company_name": company_name, "domain": task_input.get("domain")})]
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        search_res = completed_tasks[0]
        li_search_res = completed_tasks[1]
        headcount_res = completed_tasks[2]
        other_results = [completed_tasks[3], completed_tasks[4]]
        db_res = completed_tasks[5]

        # --- STAGE 1: CANONICAL DOMAIN RESOLUTION ---
        resolved_website = None
        resolved_domain = None
        
        results = search_res.data.get("results", []) if search_res and not isinstance(search_res, Exception) and hasattr(search_res, "data") else []
        
        for item in results:
            url = item.get("link", "")
            if not url:
                continue
                
            if is_aggregator(url):
                pipeline_log.append(f"AGGREGATOR_SKIP: {url} — not the target company's owned domain")
                continue
                
            if not is_path_shallow(url):
                continue
                
            # Perform a basic check for aggregator boilerplate in snippet
            snippet = item.get("snippet", "").lower()
            if any(p in snippet for p in ["is a leading provider", "profile overview", "global data", "globaldata"]):
                pipeline_log.append(f"AGGREGATOR_SKIP: {url} — description contains aggregator boilerplate")
                continue
                
            resolved_website = url
            resolved_domain = get_domain(url)
            pipeline_log.append(f"STAGE_1: canonical domain resolved → {resolved_domain}")
            break
            
        if not resolved_website:
            # Try next non-aggregator
            for item in results:
                url = item.get("link", "")
                if url and not is_aggregator(url):
                    resolved_website = url
                    resolved_domain = get_domain(url)
                    pipeline_log.append(f"STAGE_1: canonical domain resolved → {resolved_domain} (fallback)")
                    break
                    
        if not resolved_website:
            resolved_domain = f"{company_name.lower().replace(' ', '')}.com"
            resolved_website = f"https://www.{resolved_domain}"
            pipeline_log.append(f"STAGE_1: canonical domain fallback default → {resolved_domain}")
            data_quality_flags.append(f"CANONICAL_DOMAIN_FALLBACK: using default {resolved_domain}")

        # --- STAGE 2: LINKEDIN COMPANY SLUG RESOLUTION (Failure 2) ---
        linkedin_company_url = None
        linkedin_slug = None
        
        li_results = li_search_res.data.get("results", []) if li_search_res and not isinstance(li_search_res, Exception) and hasattr(li_search_res, "data") else []
        
        attempts = 0
        for item in li_results:
            url = item.get("link", "")
            if not url:
                continue
                
            import re
            match = re.search(r"linkedin\.com/company/([a-z0-9\-]+)", url.lower())
            if match:
                slug = match.group(1).strip("/")
                attempts += 1
                if slug in ("unavailable", "search", "jobs", "pub", "login"):
                    pipeline_log.append(f"LINKEDIN_SKIP: slug was /{slug}/ — retried")
                    if attempts >= 3:
                        break
                    continue
                
                linkedin_slug = slug
                linkedin_company_url = f"https://www.linkedin.com/company/{slug}"
                pipeline_log.append(f"STAGE_2: LinkedIn company slug resolved → {slug}")
                break
                
        if not linkedin_company_url:
            pipeline_log.append(f"LINKEDIN_UNRESOLVED: {company_name}")
            data_quality_flags.append(f"LINKEDIN_UNRESOLVED: LinkedIn profile not found for {company_name}")

        # --- STAGE 2: TRIGGER / SIGNAL DETECTION (headcount growth) ---
        employee_growth_rate = "Moderate"
        hc_results = headcount_res.data.get("results", []) if headcount_res and not isinstance(headcount_res, Exception) and hasattr(headcount_res, "data") else []
        
        hc_corpus = "\n".join([f"Source: {item.get('title')}: {item.get('snippet')}" for item in hc_results[:3]])

        # Gather general seed data and live search data for core enrichment
        seed_data = {}
        seed_contacts = []
        if db_res and not isinstance(db_res, Exception) and hasattr(db_res, "data"):
            seed_data = db_res.data.get("company", {})
            seed_contacts = db_res.data.get("contacts", [])
        
        # Build live search context
        queries = [
            f"{company_name} company overview website industry head office",
            f"{company_name} funding rounds tech stack tools"
        ]
        search_tasks = [self.search_tool.execute({"query": q}) for q in queries]
        other_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        raw_text_corpus = []
        articles = []
        for res in other_results:
            if isinstance(res, Exception) or not res or not hasattr(res, "data"):
                continue
            for item in res.data.get("results", []):
                title = item.get("title", "Search Source")[:100]
                snippet = item.get("snippet", "")[:300]
                link = item.get("link", "")
                
                if is_aggregator(link):
                    pipeline_log.append(f"AGGREGATOR_SKIP: {link} — not the target company's owned domain")
                    continue
                    
                if len(raw_text_corpus) < 10:
                    raw_text_corpus.append(f"Source [{title}] ({link}): {snippet}")
                if link and len(articles) < 10:
                    articles.append({
                        "title": f"Web: {title}",
                        "url": link,
                        "source": "Google/DDG Search"
                    })
                    
        corpus_string = "\n".join(raw_text_corpus)

        refinement_prompt = f"""
        You are a B2B Enrichment Specialist. Analyze the seed data and raw search snippets below to build an accurate profile of '{company_name}'.
        
        Seed Data:
        {json.dumps(seed_data, indent=2)}
        
        Live Search Context:
        {corpus_string}
        
        Headcount context:
        {hc_corpus}
        
        Extract and return a single, unified JSON object. If direct web search info contradicts the seed details, prefer the web search data.
        Return this exact JSON structure:
        {{
          "name": "{company_name}",
          "industry": "e.g. Enterprise Software / Fintech",
          "employees": integer or null,
          "founded": integer or null,
          "hq": "City, Country",
          "tech_stack": ["React", "AWS", "Workday", etc],
          "current_hr_tool": "e.g. Workday / Gusto / Excel",
          "recent_funding": {{
            "round": "e.g. Series A or null",
            "amount_usd": integer or null,
            "date": "YYYY-MM-DD or null"
          }},
          "growth_rate": "e.g. 25% headcount growth or null",
          "website": "{resolved_website}",
          "linkedin": "{linkedin_company_url or ''}",
          "description": "2-3 sentence overview of what the company does"
        }}
        """

        refined_company = seed_data
        try:
            llm_response = await self.call_llm(
                prompt=refinement_prompt,
                system_message="You are a strict data scientist. Output ONLY valid JSON. No prose. No sentence fragments in numeric fields.",
                response_format={"type": "json_object"}
            )
            refined_company = json.loads(llm_response)
        except Exception as e:
            print(f"[company_enricher] LLM refinement failed: {e}")

        # Enforce anti-hallucination constraints on outputs
        refined_company["website"] = resolved_website
        refined_company["linkedin"] = linkedin_company_url
        
        # Ensure correct type formats
        if refined_company.get("employees") and not isinstance(refined_company.get("employees"), int):
            try:
                refined_company["employees"] = int(refined_company["employees"])
            except Exception:
                refined_company["employees"] = None
        if refined_company.get("founded") and not isinstance(refined_company.get("founded"), int):
            try:
                refined_company["founded"] = int(refined_company["founded"])
            except Exception:
                refined_company["founded"] = None

        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": refined_company})
        
        return {
            "company_details": refined_company,
            "raw_enrichment_data": refined_company,
            "contacts": seed_contacts,
            "articles": articles,
            "pipeline_log": pipeline_log,
            "data_quality_flags": data_quality_flags
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
            "recent_funding": {"round": "Series A", "amount_usd": 10000000, "date": "2026-01-01"},
            "growth_rate": "Moderate",
            "website": f"https://www.{company_name.lower().replace(' ', '')}.com",
            "linkedin": f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '')}"
        }
        return {
            "company_details": fallback_details,
            "raw_enrichment_data": {},
            "contacts": [],
            "articles": []
        }
