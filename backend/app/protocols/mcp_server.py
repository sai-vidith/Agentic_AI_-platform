"""MCP (Model Context Protocol) Tool Server — exposes NexusAI tools for external agent ecosystems."""
from fastapi import APIRouter
from typing import Dict, Any, List
from datetime import datetime, timezone

router = APIRouter(prefix="/v2/mcp", tags=["MCP Protocol"])


# MCP Tool Manifest — describes available tools for external agents
MCP_TOOL_MANIFEST = {
    "schema_version": "2024-11-05",
    "server_info": {
        "name": "nexusai-mcp-server",
        "version": "3.0.0",
        "description": "NexusAI Agentic Platform — B2B Customer Discovery & Prospect Intelligence",
    },
    "tools": [
        {
            "name": "discover_leads",
            "description": "Trigger a full B2B lead discovery pipeline for a target company. Orchestrates 8 specialist agents via DAG execution.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Name of the target company to analyze"},
                    "domain": {"type": "string", "description": "Business domain for ICP matching (e.g., 'hr_saas')", "default": "hr_saas"},
                },
                "required": ["company_name"],
            },
        },
        {
            "name": "get_leads",
            "description": "Retrieve all discovered and qualified leads from the NexusAI knowledge base.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_knowledge_graph",
            "description": "Query the NexusAI knowledge graph for entity relationships (companies, people, technologies).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Name of the entity to query connections for"},
                    "depth": {"type": "integer", "description": "Depth of graph traversal", "default": 1},
                },
                "required": ["entity_name"],
            },
        },
        {
            "name": "score_company",
            "description": "Score a company against the configured Ideal Customer Profile (ICP) criteria.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "industry": {"type": "string"},
                    "employee_count": {"type": "integer"},
                    "tech_stack": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["company_name"],
            },
        },
        {
            "name": "chaos_monkey_toggle",
            "description": "Toggle the Chaos Monkey fault injection system on or off.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "description": "Whether to enable fault injection"},
                },
                "required": ["enabled"],
            },
        },
    ],
}


@router.get("/manifest")
async def get_mcp_manifest():
    """Returns the MCP tool manifest for external agent discovery."""
    return MCP_TOOL_MANIFEST


@router.post("/tools/{tool_name}/invoke")
async def invoke_mcp_tool(tool_name: str, params: Dict[str, Any] = {}):
    """Invoke an MCP tool by name. Routes to internal NexusAI services."""
    if tool_name == "discover_leads":
        from app.core.planner import planner_agent
        from app.core.dag_executor import DAGExecutor
        company = params.get("company_name", "")
        domain = params.get("domain", "hr_saas")
        if not company:
            return {"error": "company_name is required"}
        dag = await planner_agent.create_plan(domain, company)
        executor = DAGExecutor(dag)
        result = await executor.execute()
        return {"status": "completed", "result": result}
    
    elif tool_name == "get_leads":
        from app.core.event_store import event_store
        return {"leads": event_store.get_all_leads()}
    
    elif tool_name == "get_knowledge_graph":
        from app.knowledge_graph.graph import kg_manager
        entity = params.get("entity_name", "")
        depth = params.get("depth", 1)
        return kg_manager.get_subgraph_data([entity], depth=depth)
    
    elif tool_name == "score_company":
        from app.agents.icp_matcher import ICPMatcherAgent
        matcher = ICPMatcherAgent()
        result = await matcher.execute({
            "company_details": {
                "name": params.get("company_name", ""),
                "industry": params.get("industry", ""),
                "employees": params.get("employee_count", 0),
                "tech_stack": params.get("tech_stack", []),
            },
            "icp_rules": {},
        })
        return result
    
    elif tool_name == "chaos_monkey_toggle":
        from app.core.chaos_monkey import chaos_monkey
        chaos_monkey.enabled = params.get("enabled", False)
        return {"chaos_monkey_enabled": chaos_monkey.enabled}
    
    return {"error": f"Unknown tool: {tool_name}"}


@router.get("/tools")
async def list_mcp_tools():
    """List all available MCP tools (simplified view)."""
    return {
        "tools": [
            {"name": t["name"], "description": t["description"]}
            for t in MCP_TOOL_MANIFEST["tools"]
        ]
    }
