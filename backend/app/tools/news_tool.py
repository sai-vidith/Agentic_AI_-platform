import httpx
import json
from pathlib import Path
from typing import Dict, Any, List
from app.tools.base_tool import BaseTool, ToolResult, DATA_DIR
from app.config import settings

class NewsTool(BaseTool):
    """News monitoring tool wrapping NewsAPI.org or mock news feed."""
    
    def __init__(self):
        super().__init__(name="news_tool")

    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        company_name = golden_data.get("company", {}).get("name", "")
        # Find golden articles or simulate one
        news_file = DATA_DIR / "news_feed.json"
        if news_file.exists():
            with open(news_file, "r", encoding="utf-8") as f:
                articles = json.load(f)
                company_articles = [a for a in articles if company_name.lower() in a.get("company", "").lower()]
                if company_articles:
                    return {"articles": company_articles}
        
        # Fallback golden summary if feed file not read
        return {
            "articles": [
                {
                    "title": f"Recent expansion at {company_name}",
                    "content": f"{company_name} is accelerating hiring after key funding activities.",
                    "source": "TechNews",
                    "company": company_name,
                    "timestamp": "2026-06-25T12:00:00Z"
                }
            ]
        }

    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        query = params.get("query", "")
        company = params.get("company_name", "")
        search_query = query or company
        
        if not search_query:
            return ToolResult(data={"articles": []}, source="news_live")
            
        if not settings.NEWS_API_KEY or settings.NEWS_API_KEY == "mock_news_key":
            return await self._get_fallback_mock_data(search_query, params, "NewsAPI key missing")

        url = "https://newsapi.org/v2/everything"
        payload = {
            "q": search_query,
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": settings.NEWS_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=payload, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                articles = []
                for item in data.get("articles", []):
                    articles.append({
                        "title": item.get("title"),
                        "content": item.get("description") or item.get("content"),
                        "source": item.get("source", {}).get("name"),
                        "company": company or search_query,
                        "timestamp": item.get("publishedAt"),
                        "url": item.get("url") or f"https://news.google.com/search?q={item.get('title')}"
                    })
                return ToolResult(data={"articles": articles}, source="news_live_api", latency_ms=int(response.elapsed.total_seconds() * 1000))
            else:
                return await self._get_fallback_mock_data(search_query, params, f"NewsAPI returned status {response.status_code}")

    async def _get_fallback_mock_data(self, company_name: str, params: Dict[str, Any], live_error: str) -> ToolResult:
        # Load from local mock news feed if available
        feed_path = DATA_DIR / "news_feed.json"
        if feed_path.exists():
            with open(feed_path, "r", encoding="utf-8") as f:
                articles = json.load(f)
                matched = []
                for a in articles:
                    if company_name.lower() in a.get("company", "").lower() or company_name.lower() in a.get("title", "").lower():
                        source_domain = "techcrunch.com" if "crunch" in a.get("source", "").lower() else "reuters.com" if "reuters" in a.get("source", "").lower() else "venturebeat.com"
                        a["url"] = a.get("url") or f"https://{source_domain}"
                        matched.append(a)
                if matched:
                    return ToolResult(data={"articles": matched}, source="news_mock_feed", latency_ms=10)
                    
        # General mock fallback
        fallback = [
            {
                "title": f"{company_name} announces strategic plans for high-growth scaling",
                "content": f"Insiders report that {company_name} is looking to expand their technological capabilities and hire specialized executives to drive strategic execution in 2026.",
                "source": "TechDaily",
                "company": company_name,
                "timestamp": "2026-06-24T15:30:00Z",
                "url": "https://techdaily.com"
            }
        ]
        return ToolResult(data={"articles": fallback}, source="news_mock_generic", latency_ms=20, error=live_error)
