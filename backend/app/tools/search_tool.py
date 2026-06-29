import httpx
from typing import Dict, Any
from app.tools.base_tool import BaseTool, ToolResult
from app.config import settings

class SearchTool(BaseTool):
    """Google Search tool wrapping Serper.dev."""
    
    def __init__(self):
        super().__init__(name="search_tool")

    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        # Return company info & triggers as search result summary
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
            return ToolResult(data={"results": []}, source="search_live")
            
        # Try Tavily Search first if available (Tavily has a free tier of 1,000 requests/month)
        tavily_key = (settings.TAVILY_API_KEY or "").strip('"\'')
        if tavily_key and tavily_key != "mock_tavily_key" and len(tavily_key) > 5:
            try:
                url = "https://api.tavily.com/search"
                payload = {
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5
                }
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=payload, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        results = []
                        for item in data.get("results", []):
                            results.append({
                                "title": item.get("title"),
                                "snippet": item.get("content"),
                                "link": item.get("url")
                            })
                        return ToolResult(
                            data={"results": results},
                            source="search_live_tavily",
                            latency_ms=int(response.elapsed.total_seconds() * 1000)
                        )
            except Exception as e:
                print(f"Tavily search failed, trying Serper fallback: {e}")

        # Try Serper first if available
        if settings.SERPER_API_KEY and settings.SERPER_API_KEY != "mock_serper_key":
            try:
                url = "https://google.serper.dev/search"
                payload = {"q": query}
                headers = {
                    'X-API-KEY': settings.SERPER_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        organic = data.get("organic", [])
                        results = []
                        for item in organic[:5]:
                            results.append({
                                "title": item.get("title"),
                                "snippet": item.get("snippet"),
                                "link": item.get("link")
                            })
                        return ToolResult(data={"results": results}, source="search_live_serper", latency_ms=int(response.elapsed.total_seconds() * 1000))
            except Exception as e:
                print(f"Serper search failed, trying DuckDuckGo fallback: {e}")

        # Try DuckDuckGo HTML scraper fallback (completely keyless)
        import urllib.parse
        from selectolax.parser import HTMLParser
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            async with httpx.AsyncClient() as client:
                response = await client.get(ddg_url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    parser = HTMLParser(response.text)
                    results = []
                    for link_node in parser.css(".result__body")[:5]:
                        title_el = link_node.css_first(".result__title a")
                        snippet_el = link_node.css_first(".result__snippet")
                        if title_el:
                            title = title_el.text().strip()
                            href = title_el.attributes.get("href", "")
                            if "uddg=" in href:
                                parsed_href = urllib.parse.urlparse(href)
                                qs = urllib.parse.parse_qs(parsed_href.query)
                                href = qs.get("uddg", [href])[0]
                            elif href.startswith("//"):
                                href = "https:" + href
                            
                            snippet = snippet_el.text().strip() if snippet_el else ""
                            results.append({
                                "title": title,
                                "snippet": snippet,
                                "link": href
                            })
                    if results:
                        return ToolResult(
                            data={"results": results},
                            source="search_duckduckgo_fallback",
                            latency_ms=int(response.elapsed.total_seconds() * 1000)
                        )
        except Exception as e:
            print(f"DuckDuckGo fallback search failed: {e}")

        return await self._get_fallback_mock_data(query, params, "Both Serper and DuckDuckGo search failed")

    async def _get_fallback_mock_data(self, query: str, params: Dict[str, Any], live_error: str) -> ToolResult:
        # Generate some smart generic search results for standard queries
        query_lower = query.lower()
        results = [
            {
                "title": f"Recent News about {query}",
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
    import json
    from app.tools.search_tool import SearchTool
    from app.tools.llm_tool import llm_service
    
    search_tool = SearchTool()
    domain_clean = domain.replace('_', ' ')
    
    # 5 highly focused search angles targeting both global and Indian/domestic startups
    queries = [
        f"recently funded {domain_clean} startups 2026",
        f"top rising {domain_clean} companies list 2026",
        f"new {domain_clean} software products launches 2025 2026",
        f"top {domain_clean} startups in India 2025 2026",
        f"recently funded Indian B2B {domain_clean} companies"
    ]
    
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
                
    results_text = json.dumps(merged_results[:25]) # Provide up to 25 search result snippets
    
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
        content = response.choices[0].message.content
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
