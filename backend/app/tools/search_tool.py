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
