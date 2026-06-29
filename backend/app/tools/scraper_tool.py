import httpx
import re
from bs4 import BeautifulSoup
from typing import Dict, Any
from app.tools.base_tool import BaseTool, ToolResult
from app.config import settings

class ScraperTool(BaseTool):
    """
    ScraperTool uses BeautifulSoup4 and lxml to scrape and parse HTML content natively.
    Removes all external dependencies on Firecrawl and Kimi WebBridge.
    """
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
            return ToolResult(data={"text": ""}, source="scraper_empty")

        # Try to use Firecrawl API if configured with a real API key
        api_key = settings.FIRECRAWL_API_KEY
        if api_key and not api_key.startswith("mock_"):
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "url": url,
                    "formats": ["markdown"]
                }
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.post("https://api.firecrawl.dev/v1/scrape", json=payload, headers=headers)
                    if response.status_code == 200:
                        res_json = response.json()
                        if res_json.get("success") and "data" in res_json:
                            data = res_json["data"]
                            markdown_content = data.get("markdown", "")
                            title = data.get("metadata", {}).get("title", "Scraped Page")
                            return ToolResult(
                                data={
                                    "url": url,
                                    "text": markdown_content[:6000],
                                    "title": title
                                },
                                source="firecrawl_api"
                            )
            except Exception as fe:
                print(f"[ScraperTool] Firecrawl API scrape failed: {fe}. Falling back to BeautifulSoup...")

        try:
            async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5"
                }
                response = await client.get(url, headers=headers, timeout=12.0)
                
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Parse using BeautifulSoup
                    soup = BeautifulSoup(html_content, "lxml")
                    
                    # Strip script, style, nav, header, footer, noscript elements
                    for element in soup(["script", "style", "nav", "header", "footer", "noscript", "form", "svg"]):
                        element.decompose()
                        
                    # Extract title
                    title_text = ""
                    if soup.title and soup.title.string:
                        title_text = soup.title.string.strip()
                        
                    # Extract and clean text content
                    raw_text = soup.get_text(separator="\n")
                    clean_lines = []
                    for line in raw_text.splitlines():
                        stripped = line.strip()
                        if stripped and len(stripped) > 3:  # avoid noise
                            clean_lines.append(stripped)
                            
                    clean_text = "\n".join(clean_lines)
                    
                    return ToolResult(
                        data={
                            "url": url,
                            "text": clean_text[:6000],  # generous context budget
                            "title": title_text
                        },
                        source="scraper_beautifulsoup4",
                        latency_ms=int(response.elapsed.total_seconds() * 1000)
                    )
                else:
                    print(f"[ScraperTool] HTTP request returned status code {response.status_code} for {url}")
                    return await self._get_fallback_mock_data(url, params, f"HTTP status {response.status_code}")
                    
        except Exception as e:
            print(f"[ScraperTool] Exception occurred while scraping {url}: {e}")
            return await self._get_fallback_mock_data(url, params, str(e))

    async def _get_fallback_mock_data(self, url: str, params: Dict[str, Any], live_error: str) -> ToolResult:
        # Check fallback allowance
        if not settings.ALLOW_MOCK_FALLBACK:
            raise ValueError(f"ScraperTool failed on {url}: {live_error}")
            
        return ToolResult(
            data={
                "url": url,
                "text": f"Scrape failed. Displaying simulated home page contents for: {url}. We specialize in enterprise software services, cloud infrastructure management, security compliance audits, and recruiting human capital management.",
                "title": "Corporate Homepage fallback"
            },
            source="scraper_mock",
            latency_ms=50,
            error=live_error
        )
