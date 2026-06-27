from app.tools.search_tool import SearchTool
from app.tools.news_tool import NewsTool
from app.tools.scraper_tool import ScraperTool
from app.tools.enrichment_tool import EnrichmentTool
from app.tools.kg_tool import KGTool
from app.tools.rag_tool import RAGTool

# Instantiate singletons
search_tool = SearchTool()
news_tool = NewsTool()
scraper_tool = ScraperTool()
enrichment_tool = EnrichmentTool()
kg_tool = KGTool()
rag_tool = RAGTool()

# Registry
tool_registry = {
    "search_tool": search_tool,
    "news_tool": news_tool,
    "scraper_tool": scraper_tool,
    "enrichment_tool": enrichment_tool,
    "kg_tool": kg_tool,
    "rag_tool": rag_tool
}

def get_tool(name: str):
    return tool_registry.get(name)
