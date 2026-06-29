import asyncio
import json
import os
import sys
import tempfile
from typing import Dict, Any, List

class ScrapyCrawler:
    """
    ScrapyCrawler executes a Scrapy Spider in a safe background subprocess.
    This avoids Twisted reactor loop conflicts with FastAPI's asyncio loop.
    """
    
    @staticmethod
    async def crawl_url(url: str) -> Dict[str, Any]:
        """
        Crawls a target URL using Scrapy and returns the extracted HTML and text content.
        """
        # Define a minimal Scrapy Spider in a temporary file
        spider_code = f"""
import scrapy
from bs4 import BeautifulSoup
import json

class WebPageSpider(scrapy.Spider):
    name = "web_page_spider"
    start_urls = [{repr(url)}]
    
    custom_settings = {{
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_TIMEOUT': 10,
        'LOG_LEVEL': 'ERROR',
    }}

    def parse(self, response):
        soup = BeautifulSoup(response.text, "lxml")
        
        # Strip script, style, nav, footer, header
        for tag in soup(["script", "style", "nav", "footer", "header", "svg"]):
            tag.decompose()
            
        title = soup.title.string.strip() if soup.title else ""
        text = "\\n".join([line.strip() for line in soup.get_text(separator="\\n").splitlines() if line.strip()])
        
        result = {{
            "url": response.url,
            "status": response.status,
            "title": title,
            "text": text[:6000]
        }}
        
        print(json.dumps(result))
"""
        
        temp_dir = tempfile.gettempdir()
        temp_spider_path = os.path.join(temp_dir, "temp_scrapy_spider.py")
        
        try:
            with open(temp_spider_path, "w", encoding="utf-8") as f:
                f.write(spider_code)
                
            # Run Scrapy subprocess using the current python environment's scrapy executable
            python_executable = sys.executable
            # Try to locate scrapy script in Scripts directory
            scrapy_bin = os.path.join(os.path.dirname(python_executable), "scrapy")
            if not os.path.exists(scrapy_bin) and os.path.exists(scrapy_bin + ".exe"):
                scrapy_bin = scrapy_bin + ".exe"
                
            cmd = [scrapy_bin, "runspider", temp_spider_path]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0 and stdout:
                # Find the JSON line in output
                for line in stdout.decode("utf-8", errors="ignore").splitlines():
                    if line.strip().startswith("{") and line.strip().endswith("}"):
                        try:
                            return json.loads(line)
                        except Exception:
                            continue
                            
            # Fallback output
            err_msg = stderr.decode("utf-8", errors="ignore") if stderr else "No output"
            return {"url": url, "status": 500, "text": "", "error": err_msg}
            
        except Exception as e:
            return {"url": url, "status": 500, "text": "", "error": str(e)}
        finally:
            if os.path.exists(temp_spider_path):
                try:
                    os.remove(temp_spider_path)
                except Exception:
                    pass

scrapy_crawler = ScrapyCrawler()
