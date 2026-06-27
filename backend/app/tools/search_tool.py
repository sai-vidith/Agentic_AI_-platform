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
            
        if not settings.SERPER_API_KEY or settings.SERPER_API_KEY == "mock_serper_key":
            return await self._get_fallback_mock_data(query, params, "Serper API key missing")

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
                # Clean and structure results
                organic = data.get("organic", [])
                results = []
                for item in organic[:5]:
                    results.append({
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                        "link": item.get("link")
                    })
                return ToolResult(data={"results": results}, source="search_live_serper", latency_ms=int(response.elapsed.total_seconds() * 1000))
            else:
                return await self._get_fallback_mock_data(query, params, f"Serper returned status {response.status_code}")

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
