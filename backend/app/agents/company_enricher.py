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
            return {"company_details": {}, "raw_enrichment_data": {}}
            
        await notify_agent_event(WSEventTypes.AGENT_TOOL_CALL, self.name, target=company_name, data={"tool": "search_tool"})
        
        # 1. First run the standard local mock DB check for immediate fallback or seed data
        db_res = await self.enrichment_tool.execute({"company_name": company_name})
        seed_data = db_res.data.get("company", {})
        seed_contacts = db_res.data.get("contacts", [])

        # 2. Perform intensive parallel searches to gather multi-source context
        queries = [
            f"{company_name} company overview website industry head office",
            f"{company_name} funding rounds tech stack tools",
            f"{company_name} official corporate LinkedIn page profile"
        ]
        
        search_tasks = [self.search_tool.execute({"query": q}) for q in queries]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 3. Aggregate all retrieved search snippets and sources
        raw_text_corpus = []
        articles = []
        for idx, res in enumerate(search_results):
            if isinstance(res, Exception) or not res or not hasattr(res, "data"):
                continue
            for item in res.data.get("results", []):
                title = item.get("title", "Search Source")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                raw_text_corpus.append(f"Source [{title}] ({link}): {snippet}")
                if link:
                    articles.append({
                        "title": f"Web: {title}",
                        "url": link,
                        "source": "Google/DDG Search"
                    })
        
        corpus_string = "\n".join(raw_text_corpus)
        
        # 4. Invoke Cerebras/LLM to refine and merge seed details with live web results
        refinement_prompt = f"""
        You are a B2B Enrichment Specialist. Analyze the seed data and raw search snippets below to build an accurate profile of '{company_name}'.
        
        Seed Data:
        {json.dumps(seed_data, indent=2)}
        
        Live Search Context:
        {corpus_string}
        
        Extract and return a single, unified JSON object. If direct web search info contradicts the seed details, prefer the web search data.
        Return this exact JSON structure:
        {{
          "name": "{company_name}",
          "industry": "e.g. Enterprise Software / Fintech",
          "employees": integer,
          "founded": integer,
          "hq": "City, Country",
          "tech_stack": ["React", "AWS", "Workday", etc],
          "current_hr_tool": "e.g. Workday / Gusto / Excel",
          "recent_funding": {{
            "round": "e.g. Series A",
            "amount_usd": integer,
            "date": "YYYY-MM-DD"
          }},
          "growth_rate": "e.g. 25% headcount growth",
          "website": "http://verified-website.com",
          "linkedin": "http://linkedin.com/company/...",
          "description": "2-3 sentence overview of what the company does"
        }}
        """

        refined_company = seed_data
        try:
            llm_response = await self.call_llm(
                prompt=refinement_prompt,
                system_message="You are a strict data scientist. Output ONLY valid JSON.",
                response_format={"type": "json_object"}
            )
            refined_company = json.loads(llm_response)
        except Exception as e:
            print(f"[company_enricher] LLM refinement failed: {e}")

        # Ensure essential links are populated
        if not refined_company.get("website"):
            refined_company["website"] = f"https://www.{company_name.lower().replace(' ', '')}.com"
        if not refined_company.get("linkedin"):
            refined_company["linkedin"] = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '')}"

        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": refined_company})
        
        return {
            "company_details": refined_company,
            "raw_enrichment_data": refined_company,
            "contacts": seed_contacts,
            "articles": articles
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
            "raw_enrichment_data": {}
        }
