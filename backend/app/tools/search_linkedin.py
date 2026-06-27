import asyncio
from duckduckgo_search import DDGS
import json

async def search_linkedin(name: str = "", company: str = "", query: str = "", arg1: str = "") -> str:
    """Searches LinkedIn and the web to find the real LinkedIn profile and contact details of a person."""
    # Handle various argument formats from the LLM
    search_query = ""
    if name and company:
        search_query = f"{name} {company} LinkedIn"
    elif query:
        search_query = f"{query} LinkedIn"
    elif arg1:
        search_query = f"{arg1} LinkedIn"
    else:
        search_query = f"{name or company or 'unknown'} LinkedIn"
    
    loop = asyncio.get_running_loop()
    
    def _search():
        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(search_query, max_results=3)]
                # Filter to only LinkedIn results if possible
                linkedin_results = [r for r in results if "linkedin.com/in/" in r.get("href", "")]
                if linkedin_results:
                    return linkedin_results
                return results
        except Exception as e:
            return [{"error": str(e)}]
            
    results = await loop.run_in_executor(None, _search)
    return json.dumps(results)
