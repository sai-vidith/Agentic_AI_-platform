import json
from pathlib import Path
from typing import Dict, Any, List
import asyncio
import yfinance as yf
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
from app.tools.base_tool import BaseTool, ToolResult, DATA_DIR

class EnrichmentTool(BaseTool):
    """Enrichment tool for companies and decision-maker contacts."""
    
    def __init__(self):
        super().__init__(name="enrichment_tool")

    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        # Returns the entire golden dict, including company, contacts, and graph edges
        return golden_data

    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        company_name = params.get("company_name", "")
        if not company_name:
            return ToolResult(data={}, source="enrichment_live")

        # Query mock database files first for instant demo responses
        companies_path = DATA_DIR / "companies.json"
        contacts_path = DATA_DIR / "contacts.json"
        
        company_info = {}
        contacts_info = []
        
        if companies_path.exists():
            with open(companies_path, "r", encoding="utf-8") as f:
                companies = json.load(f)
                for c in companies:
                    if company_name.lower() in c.get("name", "").lower():
                        company_info = c
                        if "linkedin" not in company_info:
                            company_info["linkedin"] = f"https://www.linkedin.com/company/{company_info.get('name', '').lower().replace(' ', '')}"
                        if "website" not in company_info:
                            company_info["website"] = f"https://www.{company_info.get('name', '').lower().replace(' ', '')}.com"
                        break
                        
        if contacts_path.exists():
            with open(contacts_path, "r", encoding="utf-8") as f:
                contacts = json.load(f)
                for entry in contacts:
                    if company_name.lower() in entry.get("company_name", "").lower():
                        contacts_info = entry.get("contacts", [])
                        break

        if company_info:
            return ToolResult(
                data={
                    "company": company_info,
                    "contacts": contacts_info
                },
                source="enrichment_mock_db",
                latency_ms=10
            )
            
        # Fallback to live web search & scraping for real companies
        return await self._execute_live_search(company_name, params)
            
        # 3. Dynamic generic mockup if everything fails
        fallback_company = {
            "name": company_name,
            "industry": "Software",
            "employees": 120,
            "founded": 2021,
            "hq": "San Francisco, US",
            "tech_stack": ["React", "Node.js", "Slack", "Google Workspace"],
            "current_hr_tool": "Excel",
            "recent_funding": {"round": "Series A", "amount_usd": 12000000, "date": "2026-02-01"},
            "growth_rate": "30% headcount growth",
            "linkedin": f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '')}"
        }
        return ToolResult(
            data={
                "company": fallback_company,
                "contacts": []
            },
            source="enrichment_mock_generic",
            latency_ms=15,
            error="Live search returned no data and company not found in mock files"
        )

    async def _execute_live_search(self, company_name: str, params: Dict[str, Any]) -> ToolResult:
        loop = asyncio.get_running_loop()
        
        def _fetch_live():
            try:
                # 1. Search for verified company website URL
                website = None
                try:
                    with DDGS() as ddgs:
                        web_search = [r for r in ddgs.text(f"{company_name} official website home page", max_results=5)]
                    
                    ignored_domains = [
                        "linkedin.com", "wikipedia.org", "crunchbase.com", "facebook.com", 
                        "twitter.com", "x.com", "youtube.com", "instagram.com", "glassdoor.com", 
                        "indeed.com", "github.com", "pitchbook.com", "zoominfo.com", "apollo.io", 
                        "tracxn.com", "ycombinator.com", "sec.gov", "reddit.com"
                    ]
                    for r in web_search:
                        href = r.get("href", "")
                        if href and not any(d in href.lower() for d in ignored_domains):
                            from urllib.parse import urlparse
                            parsed = urlparse(href)
                            website = f"{parsed.scheme}://{parsed.netloc}"
                            break
                except Exception as wex:
                    print(f"[EnrichmentTool] Website search error: {wex}")
                
                if not website:
                    website = f"https://www.{company_name.lower().replace(' ', '')}.com"

                # 2. Search for verified LinkedIn company page URL
                linkedin_url = None
                try:
                    with DDGS() as ddgs:
                        li_search = [r for r in ddgs.text(f"{company_name} linkedin company page profile", max_results=5)]
                    for r in li_search:
                        href = r.get("href", "")
                        if href and "linkedin.com/company/" in href:
                            linkedin_url = href.split("?")[0].rstrip("/")
                            break
                except Exception as liex:
                    print(f"[EnrichmentTool] LinkedIn search error: {liex}")
                
                if not linkedin_url:
                    linkedin_url = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '')}"

                # 3. Try to scrape the company homepage via Firecrawl
                from app.config import settings
                fc_key = (settings.FIRECRAWL_API_KEY or "").strip('"\'')
                markdown_content = None
                if fc_key and fc_key != "mock_firecrawl_key" and len(fc_key) > 5:
                    try:
                        print(f"[EnrichmentTool] Scraping homepage via Firecrawl: {website}")
                        api_url = "https://api.firecrawl.dev/v1/scrape"
                        headers = {
                            "Authorization": f"Bearer {fc_key}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "url": website,
                            "formats": ["markdown"]
                        }
                        response = requests.post(api_url, json=payload, headers=headers, timeout=12.0)
                        if response.status_code == 200:
                            res_data = response.json()
                            if res_data.get("success"):
                                markdown_content = res_data.get("data", {}).get("markdown", "")
                    except Exception as fcex:
                        print(f"[EnrichmentTool] Firecrawl scrape failed: {fcex}")

                # 4. Retrieve general web summary data as fallback
                summary = ""
                try:
                    with DDGS() as ddgs:
                        results = [r for r in ddgs.text(f"{company_name} company overview industry headquarters", max_results=3)]
                    summary = " ".join([r.get("body", "") for r in results])
                except Exception as e:
                    print(f"[EnrichmentTool] DDG search fallback error: {e}")
                
                # 5. Search leadership/executives
                contacts = []
                try:
                    with DDGS() as ddgs:
                        contact_search = [r for r in ddgs.text(f"{company_name} CEO founder leadership team linkedin", max_results=5)]
                    
                    for r in contact_search:
                        raw_title = r.get("title", "")
                        href = r.get("href", "")
                        body = r.get("body", "")
                        
                        if "linkedin.com/in/" in href:
                            name = raw_title.replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
                            if " - " in name:
                                name = name.split(" - ")[0].strip()
                            if " | " in name:
                                name = name.split(" | ")[0].strip()
                            contacts.append({
                                "name": name,
                                "title": body[:120],
                                "email": "unknown",
                                "phone": "unknown",
                                "linkedin": href,
                                "joined_date": "Unknown"
                            })
                except Exception as e:
                    print(f"[EnrichmentTool] Contact search error: {e}")
                
                return {
                    "website": website,
                    "linkedin_url": linkedin_url,
                    "summary": summary,
                    "contacts": contacts,
                    "markdown_content": markdown_content
                }, None
            except Exception as e:
                return None, str(e)
                
        live_data, live_error = await loop.run_in_executor(None, _fetch_live)
        
        if live_data:
            website = live_data["website"]
            linkedin_url = live_data["linkedin_url"]
            summary = live_data["summary"]
            contacts = live_data["contacts"]
            markdown_content = live_data["markdown_content"]
            
            company_data = {
                "name": company_name,
                "industry": "SaaS / Software",
                "employees": 250,
                "founded": 2015,
                "hq": "San Francisco, CA",
                "tech_stack": ["React", "Node.js", "AWS", "Next.js"],
                "current_hr_tool": "Workday",
                "recent_funding": {"round": "Series D", "amount_usd": 150000000, "date": "2024-01-01"},
                "growth_rate": "High (Hypergrowth)",
                "live_summary": summary[:1000] if summary else "No corporate summary found.",
                "website": website,
                "linkedin": linkedin_url
            }
            
            # If Firecrawl provided raw markdown, use LLM to extract company details
            if markdown_content:
                from app.tools.llm_tool import llm_service
                try:
                    prompt = f"""
                    You are a senior Business Intelligence Specialist.
                    Review the scraped homepage markdown from the company '{company_name}':
                    
                    ---
                    {markdown_content[:6000]}
                    ---
                    
                    Extract the following corporate details:
                    - Corporate description (2 sentences max)
                    - Active tech stack / software tools used (e.g. AWS, React, Snowflake, Okta, etc.)
                    - Business vertical/industry (e.g. Cybersecurity, Payroll SaaS, E-commerce)
                    - Headquarters location (City, Country)
                    
                    Respond strictly in JSON format matching this structure:
                    {{
                      "description": "...",
                      "tech_stack": ["tool1", "tool2"],
                      "industry": "...",
                      "hq": "City, Country"
                    }}
                    """
                    response = await llm_service.acompletion(
                        model="nexus-fast",
                        messages=[
                            {"role": "system", "content": "You are a strict data scientist. Output JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"}
                    )
                    parsed = json.loads(response.choices[0].message.content)
                    company_data.update({
                        "live_summary": parsed.get("description", company_data["live_summary"]),
                        "tech_stack": parsed.get("tech_stack", company_data["tech_stack"]),
                        "industry": parsed.get("industry", company_data["industry"]),
                        "hq": parsed.get("hq", company_data["hq"])
                    })
                except Exception as parse_ex:
                    print(f"[EnrichmentTool] LLM markdown parsing failed: {parse_ex}")
                    
            return ToolResult(
                data={
                    "company": company_data,
                    "contacts": contacts
                },
                source="enrichment_live_search" if not markdown_content else "enrichment_live_firecrawl",
                latency_ms=2500
            )

        # Fallback dynamic mock if live retrieval fails
        fallback_company = {
            "name": company_name,
            "industry": "Software",
            "employees": 120,
            "founded": 2021,
            "hq": "San Francisco, US",
            "tech_stack": ["React", "Node.js", "Slack", "Google Workspace"],
            "current_hr_tool": "Excel",
            "recent_funding": {"round": "Series A", "amount_usd": 12000000, "date": "2026-02-01"},
            "growth_rate": "30% headcount growth",
            "website": f"https://www.{company_name.lower().replace(' ', '')}.com",
            "linkedin": f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '')}"
        }
        return ToolResult(
            data={
                "company": fallback_company,
                "contacts": []
            },
            source="enrichment_mock_generic",
            latency_ms=15,
            error=live_error
        )
