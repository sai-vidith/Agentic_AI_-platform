import httpx
from typing import Dict, Any
from app.tools.base_tool import BaseTool, ToolResult
from app.config import settings

try:
    from selectolax.parser import HTMLParser
    SELECTOLAX_AVAILABLE = True
except ImportError:
    SELECTOLAX_AVAILABLE = False


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

        use_kimi = params.get("use_kimi", False)
        
        # Helper: Scrape via local Kimi WebBridge daemon (Tier 3)
        async def scrape_via_kimi(target_url: str) -> Dict[str, Any]:
            bridge_url = "http://127.0.0.1:10086/command"
            session_name = "nexusai-audit"
            try:
                # 1. Navigate to the page in a new tab
                navigate_payload = {
                    "action": "navigate",
                    "args": {"url": target_url, "newTab": True},
                    "session": session_name
                }
                async with httpx.AsyncClient() as client:
                    res = await client.post(bridge_url, json=navigate_payload, timeout=10.0)
                    if res.status_code != 200:
                        return {"text": "", "error": f"Kimi navigate failed: {res.text}"}
                        
                    # Wait 3 seconds for Javascript rendering & anti-bot checks to pass
                    await asyncio.sleep(3.0)
                    
                    # 2. Extract DOM innerText via evaluate
                    eval_payload = {
                        "action": "evaluate",
                        "args": {"code": "document.body.innerText"},
                        "session": session_name
                    }
                    res_eval = await client.post(bridge_url, json=eval_payload, timeout=10.0)
                    text_content = ""
                    if res_eval.status_code == 200:
                        eval_data = res_eval.json()
                        text_content = eval_data.get("value", "")
                        
                    # 3. Retrieve Page Title
                    title_payload = {
                        "action": "evaluate",
                        "args": {"code": "document.title"},
                        "session": session_name
                    }
                    res_title = await client.post(bridge_url, json=title_payload, timeout=5.0)
                    title = "Scraped Page"
                    if res_title.status_code == 200:
                        title = res_title.json().get("value", "Scraped Page")
                        
                    # 4. Close the tab to keep user browser clean
                    close_payload = {
                        "action": "close_tab",
                        "session": session_name
                    }
                    await client.post(bridge_url, json=close_payload, timeout=5.0)
                    
                    return {
                        "text": text_content[:5000],
                        "title": title,
                        "url": target_url
                    }
            except Exception as e:
                return {"text": "", "error": str(e)}

        # Direct Kimi WebBridge Activation
        if use_kimi:
            res_kimi = await scrape_via_kimi(url)
            if res_kimi.get("text"):
                return ToolResult(
                    data={
                        "url": url,
                        "text": res_kimi["text"],
                        "title": res_kimi["title"]
                    },
                    source="scraper_kimi_webbridge",
                    latency_ms=4000
                )

        # 1. Firecrawl API Path (Tier 2)
        if settings.FIRECRAWL_API_KEY and settings.FIRECRAWL_API_KEY != "mock_firecrawl_key":
            firecrawl_url = "https://api.firecrawl.dev/v2/scrape"
            payload = {"url": url}
            headers = {"Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
            try:
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
            except Exception as e:
                print(f"Firecrawl scrape failed, falling back to HTTP: {e}")

        # 2. Direct HTTP + HTML Parsing Path (Tier 1)
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                response = await client.get(url, headers=headers, timeout=10.0)
                
                # Auto-escalation: If direct HTTP fails or is blocked (403, 401, 503)
                if response.status_code in [403, 401, 503, 400]:
                    print(f"[ScraperTool] HTTP status {response.status_code} (Blocked). Escalating to local Kimi WebBridge...")
                    res_kimi = await scrape_via_kimi(url)
                    if res_kimi.get("text"):
                        return ToolResult(
                            data={
                                "url": url,
                                "text": res_kimi["text"],
                                "title": res_kimi["title"]
                            },
                            source="scraper_kimi_webbridge_escalation",
                            latency_ms=4500
                        )
                
                if response.status_code == 200:
                    html = response.text

                    if SELECTOLAX_AVAILABLE:
                        # Selectolax fast parsing
                        parser = HTMLParser(html)
                        for tag in parser.css('script, style, nav, footer, header'):
                            for el in tag:
                                el.decompose()
                        body_text = parser.body.text(separator='\n') if parser.body else ""
                        clean_text = "\n".join([line.strip() for line in body_text.splitlines() if line.strip()])
                        title_el = parser.css_first('title')
                        title_text = title_el.text() if title_el else ""
                    else:
                        # Basic fallback: strip HTML tags with regex
                        import re
                        clean_text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                        clean_text = re.sub(r'<style[^>]*>.*?</style>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
                        clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
                        clean_text = "\n".join([line.strip() for line in clean_text.splitlines() if line.strip()])
                        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
                        title_text = title_match.group(1).strip() if title_match else ""

                    return ToolResult(
                        data={
                            "url": url,
                            "text": clean_text[:4000],
                            "title": title_text
                        },
                        source="scraper_selectolax" if SELECTOLAX_AVAILABLE else "scraper_regex",
                        latency_ms=int(response.elapsed.total_seconds() * 1000)
                    )
                else:
                    return await self._get_fallback_mock_data(url, params, f"HTTP status {response.status_code}")
        except Exception as http_ex:
            # Fallback to Kimi WebBridge on connection/HTTP exceptions too!
            print(f"[ScraperTool] HTTP request failed ({http_ex}). Attempting Kimi WebBridge fallback...")
            res_kimi = await scrape_via_kimi(url)
            if res_kimi.get("text"):
                return ToolResult(
                    data={
                        "url": url,
                        "text": res_kimi["text"],
                        "title": res_kimi["title"]
                    },
                    source="scraper_kimi_webbridge_fallback",
                    latency_ms=4500
                )
            return await self._get_fallback_mock_data(url, params, str(http_ex))

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
