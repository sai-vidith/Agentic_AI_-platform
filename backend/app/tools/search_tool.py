import httpx
import json
import re
import urllib.parse
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
from app.tools.base_tool import BaseTool, ToolResult
from app.config import settings
from app.tools.llm_tool import llm_service

class SearchTool(BaseTool):
    """
    SearchTool provides keyless search capabilities by scraping DuckDuckGo HTML results natively.
    Removes all external dependencies on commercial APIs (Serper.dev, Tavily).
    """
    def __init__(self):
        super().__init__(name="search_tool")

    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        company = golden_data.get("company", {})
        triggers = golden_data.get("triggers", [])
        return {
            "results": [
                {
                    "title": f"{company.get('name')} Overview",
                    "snippet": f"HQ: {company.get('hq')}. Industry: {company.get('industry')}. Founded: {company.get('founded')}. Employees: {company.get('employees')}. Growth: {company.get('growth_rate')}.",
                    "link": f"https://{company.get('name', 'company').lower().replace(' ', '')}.com"
                }
            ] + [
                {
                    "title": f"Signal: {t.get('type')}",
                    "snippet": t.get("detail"),
                    "link": "https://techcrunch.com"
                } for t in triggers
            ]
        }

    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        query = params.get("query", "")
        if not query:
            return ToolResult(data={"results": []}, source="search_empty")

        ddg_res = await self._run_ddg_html_search(query)
        if ddg_res and ddg_res.data.get("results"):
            return ddg_res

        return await self._get_fallback_mock_data(query, params, "DuckDuckGo search failed or rate-limited")

    async def _run_ddg_html_search(self, query: str) -> Optional[ToolResult]:
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(ddg_url, headers=headers, timeout=12.0)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "lxml")
                    results = []
                    
                    # DuckDuckGo HTML results list is structured with class "result__body"
                    for result in soup.find_all("div", class_="result__body")[:5]:
                        title_el = result.find("a", class_="result__url")
                        snippet_el = result.find("a", class_="result__snippet") or result.find(class_="result__snippet")
                        
                        if title_el:
                            title = title_el.get_text().strip()
                            href = title_el.get("href", "")
                            
                            # Clean uddg query param from DDG redirect url if present
                            if "uddg=" in href:
                                parsed_href = urllib.parse.urlparse(href)
                                qs = urllib.parse.parse_qs(parsed_href.query)
                                href = qs.get("uddg", [href])[0]
                            elif href.startswith("//"):
                                href = "https:" + href
                                
                            snippet = snippet_el.get_text().strip() if snippet_el else ""
                            results.append({
                                "title": title,
                                "snippet": snippet,
                                "link": href
                            })
                            
                    if results:
                        return ToolResult(
                            data={"results": results},
                            source="search_beautifulsoup4_ddg",
                            latency_ms=int(response.elapsed.total_seconds() * 1000)
                        )
        except Exception as e:
            print(f"[SearchTool] DuckDuckGo search exception: {e}")
        return None

    async def _get_fallback_mock_data(self, query: str, params: Dict[str, Any], live_error: str) -> ToolResult:
        if not settings.ALLOW_MOCK_FALLBACK:
            raise ValueError(f"SearchTool failed on query '{query}': {live_error}")
            
        results = [
            {
                "title": f"Recent news about {query}",
                "snippet": f"Startup {query} is seeing significant traction, expanding operations and hiring across core departments.",
                "link": "https://news.google.com"
            },
            {
                "title": f"{query} Company Profile - Crunchbase",
                "snippet": f"{query} details: funding rounds, leadership teams, employee growth metrics and technology stack overview.",
                "link": "https://crunchbase.com"
            }
        ]
        return ToolResult(data={"results": results}, source="search_mock", latency_ms=50, error=live_error)

async def discover_companies_from_web(domain: str, limit: int = 5) -> list[str]:
    """Runs multiple intensive search queries to discover a broad pool of B2B target startups."""
    import asyncio
    
    # Check custom mock file first (Latency and Custom Domain optimization)
    from app.config import BASE_DIR
    mock_file = BASE_DIR / "app" / "mock_data" / f"{domain}_mock.json"
    if mock_file.exists():
        try:
            with open(mock_file, "r", encoding="utf-8") as f:
                mock_data = json.load(f)
                companies = []
                if isinstance(mock_data, list):
                    companies = [c.get("name") for c in mock_data if c.get("name")]
                elif isinstance(mock_data, dict):
                    companies = mock_data.get("companies", [])
                if companies:
                    return companies[:limit]
        except Exception as e:
            print(f"Error loading custom mock file: {e}")

    # Load trigger keywords dynamically from the active domain's trigger config file
    import yaml
    from app.config import BUSINESS_CONFIG_DIR
    triggers_file = BUSINESS_CONFIG_DIR / "triggers" / f"{domain}_triggers.yaml"
    trigger_keywords = []
    if triggers_file.exists():
        try:
            with open(triggers_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if isinstance(config, dict):
                    triggers = config.get("triggers", [])
                    for t in triggers:
                        if isinstance(t, dict):
                            trigger_keywords.extend(t.get("keywords", []))
        except Exception as e:
            print(f"Error loading triggers configuration for company discovery: {e}")

    search_tool = SearchTool()
    domain_clean = domain.replace('_', ' ')
    
    # Focused search angles targeting both global and Indian/domestic startups
    queries = [
        f"recently funded {domain_clean} startups 2026",
        f"top rising {domain_clean} companies list 2026",
        f"new {domain_clean} software products launches 2025 2026",
        f"top {domain_clean} startups in India 2025 2026",
        f"recently funded Indian B2B {domain_clean} companies"
    ]
    
    # Append dynamic trigger-keyword news searches to increase coverage and accuracy
    for kw in trigger_keywords[:4]:
        queries.append(f"news \"{kw}\" startup funding 2025 2026")
        queries.append(f"\"{kw}\" company launch list 2026")
    
    # Run in parallel
    tasks = [search_tool.execute({"query": q}) for q in queries]
    search_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Merge and deduplicate links
    merged_results = []
    seen_links = set()
    for res in search_results:
        if isinstance(res, Exception) or not res or not hasattr(res, "data"):
            continue
        for item in res.data.get("results", []):
            link = item.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                merged_results.append(item)
                
    # Keep only the top 10 results and truncate snippets to prevent exceeding model limits
    clean_results = []
    for item in merged_results[:10]:
        clean_results.append({
            "title": item.get("title", "")[:100],
            "snippet": item.get("snippet", "")[:300],
            "link": item.get("link", "")
        })
    results_text = json.dumps(clean_results)
    
    prompt = f"""
    Analyze the following search results about '{domain_clean}' startups:
    {results_text}
    
    Extract a list of exactly up to {limit} distinct company names that are mentioned as active startups or businesses in this domain. 
    Ensure you include a mix of leading global startups and prominent domestic/Indian startups where applicable.
    Do not return generic portal names, directories, or news blogs.
    
    Respond in JSON format:
    {{
      "companies": ["Company A", "Company B"]
    }}
    """
    
    discovered_companies = []
    try:
        response = await llm_service.acompletion(
            model="nexus-fast",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # Parse LiteLLM completion output format safely
        content = ""
        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content
        elif isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"]
            
        data = json.loads(content)
        discovered_companies = data.get("companies", [])
    except Exception as e:
        print(f"Company extraction failed during intensive search: {e}")
        
    # Fallback to key targets including domestic/Indian startups if empty
    if not discovered_companies:
        if domain == "hr_saas":
            discovered_companies = ["Rippling", "Keka HR", "Darwinbox", "Deel"][:limit]
        else:
            discovered_companies = ["Wiz", "Securden", "Armis", "Snyk"][:limit]
            
    return discovered_companies
