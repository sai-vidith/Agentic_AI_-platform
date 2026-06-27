import asyncio
from duckduckgo_search import DDGS
import json

async def search_linkedin(name: str, company: str) -> str:
    """Searches LinkedIn and the web to find the email and phone number of a person at a company."""
    query = f"{name} {company} LinkedIn contact email phone"
    
    loop = asyncio.get_running_loop()
    
    def _search():
        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=3)]
                return results
        except Exception as e:
            return [{"error": str(e)}]
            
    results = await loop.run_in_executor(None, _search)
    return json.dumps(results)
