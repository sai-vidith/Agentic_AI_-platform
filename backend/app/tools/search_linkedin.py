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
            
    results = []
    try:
        results = await loop.run_in_executor(None, _search)
    except Exception as e:
        results = [{"error": str(e)}]
        
    # Check if DDG search returned errors or empty results, and fall back to Serper/Google Search tool
    if not results or (isinstance(results, list) and results and "error" in results[0]):
        print(f"[search_linkedin] DuckDuckGo search failed or rate-limited. Using Google/Serper SearchTool fallback...")
        try:
            from app.tools.search_tool import SearchTool
            search_tool = SearchTool()
            tool_res = await search_tool.execute({"query": search_query})
            if tool_res and hasattr(tool_res, "data") and tool_res.data:
                # Map SearchTool properties to match DDG output formats ("title", "snippet", "link" as "href")
                fallback_results = []
                for item in tool_res.data.get("results", []):
                    fallback_results.append({
                        "title": item.get("title", ""),
                        "body": item.get("snippet", ""),
                        "href": item.get("link", "")
                    })
                return json.dumps(fallback_results)
        except Exception as fe:
            print(f"[search_linkedin] SearchTool fallback failed: {fe}")
            
    return json.dumps(results)
