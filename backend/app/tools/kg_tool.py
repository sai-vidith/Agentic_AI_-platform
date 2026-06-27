from typing import Dict, Any, List
from app.tools.base_tool import BaseTool, ToolResult
from app.knowledge_graph.graph import kg_manager

class KGTool(BaseTool):
    """Tool for querying and writing to the Knowledge Graph."""
    
    def __init__(self):
        super().__init__(name="kg_tool")

    def _slice_golden_data(self, golden_data: Dict[str, Any]) -> Any:
        # Returns the raw knowledge graph edges defined in the golden path
        edges = golden_data.get("knowledge_graph_edges", [])
        return {"connections": edges}

    async def _execute_live(self, params: Dict[str, Any]) -> ToolResult:
        action = params.get("action", "query") # "query" or "add_node" or "add_relation"
        entity_name = params.get("entity_name", "")
        
        if action == "query":
            if not entity_name:
                return ToolResult(data={"connections": []}, source="kg_query")
            conns = kg_manager.query_connections(entity_name)
            formatted = []
            for u, rel, v in conns:
                formatted.append({"from": u, "rel": rel, "to": v})
            return ToolResult(data={"connections": formatted}, source="kg_query", latency_ms=5)
            
        elif action == "add_node":
            entity_type = params.get("entity_type", "unknown")
            attributes = params.get("attributes", {})
            kg_manager.add_entity(entity_name, entity_type, attributes)
            return ToolResult(data={"status": "success", "message": f"Added node {entity_name}"}, source="kg_write", latency_ms=5)
            
        elif action == "add_relation":
            source = params.get("source", "")
            target = params.get("target", "")
            relation = params.get("relation", "")
            if source and target and relation:
                kg_manager.add_relation(source, target, relation)
                return ToolResult(data={"status": "success", "message": f"Added relation {source} -[{relation}]-> {target}"}, source="kg_write", latency_ms=5)
                
        return ToolResult(data={"error": "Invalid action or parameters"}, source="kg_error", error="Invalid action")
