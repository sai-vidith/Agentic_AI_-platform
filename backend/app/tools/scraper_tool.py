import httpx
from selectolax.parser import HTMLParser
from typing import Dict, Any
from app.tools.base_tool import BaseTool, ToolResult
from app.config import settings

class ScraperTool(BaseTool):
    """Scraper tool using Selectolax for HTML parsing or Firecrawl API."""
    
    def __init__(self):
        super().__init__(name="scraper_tool")

    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        company = golden_data.get("company", {})
        return {
            "url": f"https://{company.get('name', 'company').lower().replace(' ', '')}.com",
            "text": f"Welcome to the homepage of {company.get('name')}. We are active in the {company.get('industry')} sector. Our team currently consists of {company.get('employees')} employees. We are headquartered in {company.get('hq')}.",
            "title": company.get("name"),
            "tech_stack": company.get("tech_stack", [])
        }

    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        url = params.get("url", "")
        if not url:
            return ToolResult(data={"text": ""}, source="scraper_live")

        # 1. Firecrawl API Path
        if settings.FIRECRAWL_API_KEY and settings.FIRECRAWL_API_KEY != "mock_firecrawl_key":
            firecrawl_url = "https://api.firecrawl.dev/v2/scrape"
            payload = {"url": url}
            headers = {"Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
            async with httpx.AsyncClient() as client:
                response = await client.post(firecrawl_url, json=payload, headers=headers, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    return ToolResult(
                        data={
                            "url": url,
                            "text": data.get("data", {}).get("markdown", "") or data.get("data", {}).get("content", ""),
                            "title": data.get("data", {}).get("metadata", {}).get("title", "")
                        },
                        source="scraper_firecrawl_v2",
                        latency_ms=int(response.elapsed.total_seconds() * 1000)
                    )

        # 2. Selectolax Fast Parsing Path
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                html = response.text
                parser = HTMLParser(html)
                
                # Extract text
                for tag in parser.css('script, style, nav, footer, header'):
                    for el in tag:
                        el.decompose()
                
                body_text = parser.body.text(separator='\n') if parser.body else ""
                clean_text = "\n".join([line.strip() for line in body_text.splitlines() if line.strip()])
                title = parser.css_first('title')
                title_text = title.text() if title else ""
                
                return ToolResult(
                    data={
                        "url": url,
                        "text": clean_text[:4000],  # Truncate to limit tokens
                        "title": title_text
                    },
                    source="scraper_selectolax",
                    latency_ms=int(response.elapsed.total_seconds() * 1000)
                )
            else:
                return await self._get_fallback_mock_data(url, params, f"HTTP status {response.status_code}")

    async def _get_fallback_mock_data(self, url: str, params: Dict[str, Any], live_error: str) -> ToolResult:
        return ToolResult(
            data={
                "url": url,
                "text": f"Scrape failed. Displaying simulated home page contents for: {url}. We specialize in scaling businesses with high quality services.",
                "title": "Welcome Page"
            },
            source="scraper_mock",
            latency_ms=50,
            error=live_error
        )
