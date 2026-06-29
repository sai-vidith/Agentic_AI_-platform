from typing import Dict, Any, List
import json
import asyncio
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes
from app.tools.search_tool import SearchTool
from app.tools.enrichment_tool import EnrichmentTool
from app.agents.enrichment_utils import (
    dedupe_contacts,
    is_aggregator_url,
    is_shallow_company_url,
    normalize_company_details,
    normalize_url,
)

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

        # --- 1. Primary Search using DuckDuckGo Search (DDGS) ---
        ddg_results = []
        ddg_failed = False
        pipeline_log.append("STAGE_0: Attempting primary DuckDuckGo search (DDGS)")
        try:
            ddg_res = await self.search_tool.execute({"query": f'"{company_name}" website OR CEO OR CTO OR contact details', "force_ddg": True})
            if ddg_res and hasattr(ddg_res, "data") and ddg_res.data.get("results"):
                ddg_results = ddg_res.data["results"]
                pipeline_log.append(f"STAGE_0: DDGS search returned {len(ddg_results)} results.")
            else:
                ddg_failed = True
                pipeline_log.append("STAGE_0: DDGS search returned zero results.")
        except Exception as e:
            ddg_failed = True
            pipeline_log.append(f"STAGE_0: DDGS search failed: {e}")

        # --- 2. Fallback to Local Scraper if DDGS fails ---
        scraped_text = ""
        resolved_website = None
        
        if ddg_failed or not ddg_results:
            pipeline_log.append("STAGE_1: DDGS search failed. Initiating Local HTML Fallback Scraper...")
            try:
                # Search company name using fallback query
                search_fallback = await self.search_tool.execute({"query": company_name})
                if search_fallback and hasattr(search_fallback, "data") and search_fallback.data.get("results"):
                    # Open the first search result link (skipping known third-party aggregators)
                    for item in search_fallback.data["results"]:
                        link = item.get("link", "")
                        if link and not is_aggregator_url(link):
                            resolved_website = link
                            break
                
                if resolved_website:
                    pipeline_log.append(f"STAGE_1: Opening first search result website: {resolved_website}")
                    from app.tools.scraper_tool import ScraperTool
                    scraper = ScraperTool()
                    # Scrape page text contents
                    scrape_res = await scraper.execute({"url": resolved_website})
                    if scrape_res and hasattr(scrape_res, "data") and scrape_res.data.get("text"):
                        scraped_text = scrape_res.data["text"]
                        pipeline_log.append(f"STAGE_1: Local HTML fallback scraped {len(scraped_text)} characters successfully.")
                    else:
                        pipeline_log.append("STAGE_1: Local HTML fallback scrape returned no text.")
            except Exception as ex:
                pipeline_log.append(f"STAGE_1: Local HTML fallback scraper failed: {ex}")
                
        # Resolve website from DDG results if not already resolved
        if not resolved_website and ddg_results:
            for item in ddg_results:
                url = item.get("link", "")
                if url and not is_aggregator_url(url) and is_shallow_company_url(url):
                    resolved_website = url
                    break
            if not resolved_website:
                for item in ddg_results:
                    url = item.get("link", "")
                    if url and not is_aggregator_url(url):
                        resolved_website = url
                        break
                        
        if not resolved_website:
            resolved_domain = f"{company_name.lower().replace(' ', '')}.com"
            resolved_website = f"https://www.{resolved_domain}"
            pipeline_log.append(f"STAGE_1: Canonical website default fallback: {resolved_website}")
            data_quality_flags.append(f"CANONICAL_DOMAIN_FALLBACK: using default {resolved_website}")
        else:
            pipeline_log.append(f"STAGE_1: Canonical website resolved: {resolved_website}")

        # Try to resolve corporate LinkedIn company slug from search results
        linkedin_company_url = None
        all_found_results = ddg_results if ddg_results else []
        if not all_found_results:
            # Check fallback results
            try:
                li_fallback = await self.search_tool.execute({"query": f'"{company_name}" site:linkedin.com/company'})
                if li_fallback and hasattr(li_fallback, "data") and li_fallback.data.get("results"):
                    all_found_results.extend(li_fallback.data["results"])
            except Exception:
                pass
                
        import re
        for item in all_found_results:
            url = item.get("link", "")
            if not url:
                continue
            match = re.search(r"linkedin\.com/company/([a-z0-9\-]+)", url.lower())
            if match:
                slug = match.group(1).strip("/")
                if slug not in ("unavailable", "search", "jobs", "pub", "login"):
                    linkedin_company_url = f"https://www.linkedin.com/company/{slug}"
                    pipeline_log.append(f"STAGE_2: LinkedIn corporate slug resolved: {slug}")
                    break

        if not linkedin_company_url:
            pipeline_log.append(f"STAGE_2: LinkedIn company page unresolved.")
            data_quality_flags.append(f"LINKEDIN_UNRESOLVED: Corporate LinkedIn URL not found for {company_name}")

        # --- 3. Build context for LLM extraction pass ---
        db_res = await self.enrichment_tool.execute({"company_name": company_name})
        seed_data = {}
        seed_contacts = []
        if db_res and not isinstance(db_res, Exception) and hasattr(db_res, "data"):
            seed_data = db_res.data.get("company", {})
            seed_contacts = db_res.data.get("contacts", [])

        # Compile corpus string
        raw_text_corpus = []
        articles = []
        if ddg_results:
            for item in ddg_results[:6]:
                title = item.get("title", "")[:100]
                snippet = item.get("snippet", "")[:300]
                link = item.get("link", "")
                if link:
                    raw_text_corpus.append(f"Source [{title}] ({link}): {snippet}")
                    articles.append({
                        "title": f"DDG: {title}",
                        "url": link,
                        "source": "DuckDuckGo Search"
                    })
        if scraped_text:
            raw_text_corpus.append(f"Scraped Website Content of {resolved_website}:\n{scraped_text[:3000]}")
            articles.append({
                "title": f"Website Scraped: {company_name}",
                "url": resolved_website,
                "source": "BeautifulSoup Scraper"
            })
            
        corpus_string = "\n".join(raw_text_corpus)

        refined_company = seed_data
        discovered_contacts = []
        try:
            from app.tools.chat4data import chat4data
            chat4_res = await chat4data.execute({
                "text": corpus_string,
                "company_name": company_name,
                "domain": self.domain if hasattr(self, "domain") else "hr_saas"
            })
            if chat4_res and not chat4_res.error:
                refined_company = chat4_res.data.get("company_details", seed_data)
                discovered_contacts = chat4_res.data.get("contacts", [])
        except Exception as e:
            print(f"[company_enricher] Chat4Data extraction failed: {e}")

        # Enforce anti-hallucination constraints and normalize the shared company contract.
        refined_company = normalize_company_details(company_name, refined_company)
        refined_company["website"] = normalize_url(resolved_website)
        refined_company["linkedin"] = normalize_url(linkedin_company_url, linkedin_kind="company")
        # Merge discovered contacts with seed contacts
        final_contacts = []
        seen_names = set()
        
        # 1. First add seed contacts
        for c in seed_contacts:
            name = c.get("name", "").strip().lower()
            if name:
                seen_names.add(name)
                final_contacts.append(c)
                
        # 2. Add newly discovered contacts from LLM extraction
        for c in discovered_contacts:
            name = c.get("name", "").strip().lower()
            if name and name not in seen_names:
                seen_names.add(name)
                final_contacts.append({
                    "name": c.get("name"),
                    "title": c.get("title", "Executive"),
                    "email": c.get("email") or "unknown",
                    "phone": c.get("phone") or "unknown",
                    "linkedin": c.get("linkedin") or "unknown",
                    "persona_rank": len(final_contacts) + 1,
                    "role": c.get("role") or "Influencer"
                })

        final_contacts = dedupe_contacts(final_contacts, default_source_url=refined_company.get("website", ""))

        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": refined_company})
        
        return {
            "company_details": refined_company,
            "raw_enrichment_data": {"company": refined_company, "contacts": final_contacts},
            "contacts": final_contacts,
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
            "raw_enrichment_data": {"company": fallback_details, "contacts": []},
            "contacts": [],
            "articles": []
        }




