from typing import Dict, Any, List
from app.tools.base_tool import BaseTool, ToolResult
from app.core.memory import vector_store

class RAGTool(BaseTool):
    """Tool for inserting and querying semantically stored documents."""
    
    def __init__(self):
        super().__init__(name="rag_tool")

    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        company = golden_data.get("company", {})
        triggers = golden_data.get("triggers", [])
        text = f"Company Profile: {company.get('name')}. Triggers: " + ", ".join([t.get("detail") for t in triggers])
        return {
            "results": [
                {
                    "id": company.get("name", "company_id").lower().replace(" ", "_"),
                    "text": text,
                    "metadata": {"company": company.get("name")}
                }
            ]
        }

    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        action = params.get("action", "query") # "query" or "insert"
        
        if action == "query":
            query = params.get("query", "")
            limit = params.get("limit", 5)
            if not query:
                return ToolResult(data={"results": []}, source="rag_query")
            results = vector_store.similarity_search(query, limit)
            return ToolResult(data={"results": results}, source="rag_query", latency_ms=10)
            
        elif action == "insert":
            doc_id = params.get("doc_id", "")
            text = params.get("text", "")
            metadata = params.get("metadata", {})
            if doc_id and text:
                vector_store.add_document(doc_id, text, metadata)
                return ToolResult(data={"status": "success", "message": f"Inserted document {doc_id}"}, source="rag_write", latency_ms=10)
                
        return ToolResult(data={"error": "Invalid action or parameters"}, source="rag_error", error="Invalid action")
