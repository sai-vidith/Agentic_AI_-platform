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

        # Rotate common user-agents to avoid simple anti-scraping blocks
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]

        import random
        import html

        try:
            # Enable connection pooling and compression automatically via HTTPX
            async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
                headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive"
                }
                response = await client.get(url, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Pre-cleaning regex filter: remove heavy tags BEFORE parsing into DOM.
                    # This saves up to 90% CPU/Memory overhead for BeautifulSoup on large pages.
                    html_content = re.sub(r"<(head|script|style|svg|canvas|noscript|footer|header|nav)\b[^>]*>([\s\S]*?)<\/\1>", "", html_content, flags=re.IGNORECASE)
                    
                    # Resilience fallback for lxml vs html.parser
                    try:
                        soup = BeautifulSoup(html_content, "lxml")
                    except Exception:
                        soup = BeautifulSoup(html_content, "html.parser")
                    
                    # Strip residual tag types if any missed by regex
                    for element in soup(["script", "style", "nav", "header", "footer", "noscript", "form", "svg"]):
                        element.decompose()
                        
                    # Extract title
                    title_text = ""
                    if soup.title and soup.title.string:
                        title_text = soup.title.string.strip()
                        
                    # Extract and clean text content
                    raw_text = soup.get_text(separator="\n")
                    # Unescape HTML entities (e.g. &amp; -> &, &quot; -> ")
                    raw_text = html.unescape(raw_text)
                    
                    clean_lines = []
                    for line in raw_text.splitlines():
                        # Normalize internal spacing
                        stripped = " ".join(line.split())
                        if stripped and len(stripped) > 3:  # avoid layout noise/junk
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
