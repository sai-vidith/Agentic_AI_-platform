"""A2A (Agent-to-Agent) Protocol — Agent Card discovery and inter-agent communication."""
from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime, timezone

router = APIRouter(prefix="/v2/a2a", tags=["A2A Protocol"])

# Google A2A Agent Card Specification
# See: https://google.github.io/A2A/specification/
AGENT_CARD = {
    "name": "NexusAI Lead Discovery Agent",
    "description": "An intelligent B2B customer discovery and prospect intelligence platform. "
                   "Orchestrates 8 specialist AI agents to identify, qualify, and enrich leads.",
    "url": "http://localhost:8000/v2/a2a",
    "version": "3.0.0",
    "provider": {
        "organization": "XL Ventures AI",
        "url": "https://xlventures.ai",
    },
    "capabilities": {
        "streaming": True,
        "pushNotifications": False,
        "stateTransitionHistory": True,
    },
    "authentication": {
        "schemes": ["none"],  # For hackathon demo — production would use OAuth2
    },
    "defaultInputModes": ["text/plain", "application/json"],
    "defaultOutputModes": ["application/json"],
    "skills": [
        {
            "id": "lead_discovery",
            "name": "Lead Discovery",
            "description": "Discover and qualify B2B leads by analyzing trigger events, "
                          "enriching company data, scoring ICP fit, and identifying decision-makers.",
            "tags": ["b2b", "sales", "lead-generation", "ai-agents"],
            "examples": [
                "Find leads in the HR SaaS space",
                "Qualify RazorX Fintech as a potential customer",
                "Discover companies that recently raised Series A funding",
            ],
        },
        {
            "id": "knowledge_graph_query",
            "name": "Knowledge Graph Query",
            "description": "Query the NexusAI knowledge graph for company relationships, "
                          "competitive landscapes, and technology stack patterns.",
            "tags": ["knowledge-graph", "entity-relations", "intelligence"],
            "examples": [
                "What companies use Python and AWS?",
                "Who are the competitors of RazorX?",
                "Show me all contacts at companies funded by Sequoia",
            ],
        },
        {
            "id": "icp_scoring",
            "name": "ICP Scoring",
            "description": "Score any company against configurable Ideal Customer Profile criteria.",
            "tags": ["icp", "scoring", "qualification"],
            "examples": [
                "Score Acme Corp against our HR SaaS ICP",
                "Is this company a good fit for our product?",
            ],
        },
    ],
}


@router.get("/.well-known/agent.json")
async def get_agent_card():
    """Returns the A2A Agent Card for agent discovery.
    
    External agents (e.g., Google ADK, LangChain) can discover this agent's capabilities
    by fetching this endpoint. This follows the Google A2A specification.
    """
    return AGENT_CARD


@router.get("/card")
async def get_agent_card_alias():
    """Alias for agent card (easier to remember)."""
    return AGENT_CARD


@router.post("/tasks/send")
async def receive_a2a_task(task: Dict[str, Any]):
    """Receive a task from another A2A-compatible agent.
    
    The incoming task is routed to the appropriate NexusAI skill based on the task message.
    """
    task_id = task.get("id", f"a2a_{int(datetime.now(timezone.utc).timestamp())}")
    skill_id = task.get("skill_id", "lead_discovery")
    message = task.get("message", {})
    
    if skill_id == "lead_discovery":
        from app.core.planner import planner_agent
        from app.core.dag_executor import DAGExecutor
        
        company = message.get("company_name", message.get("text", ""))
        domain = message.get("domain", "hr_saas")
        
        if not company:
            return {
                "id": task_id,
                "status": {"state": "failed"},
                "error": "No company_name provided in message",
            }
        
        try:
            dag = await planner_agent.create_plan(domain, company)
            executor = DAGExecutor(dag)
            result = await executor.execute()
            return {
                "id": task_id,
                "status": {"state": "completed"},
                "artifacts": [
                    {
                        "name": "lead_report",
                        "parts": [{"type": "application/json", "data": result}],
                    }
                ],
            }
        except Exception as e:
            return {
                "id": task_id,
                "status": {"state": "failed"},
                "error": str(e),
            }
    
    elif skill_id == "knowledge_graph_query":
        from app.knowledge_graph.graph import kg_manager
        entity = message.get("entity_name", message.get("text", ""))
        data = kg_manager.get_subgraph_data([entity], depth=2)
        return {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [
                {"name": "kg_subgraph", "parts": [{"type": "application/json", "data": data}]},
            ],
        }
    
    return {
        "id": task_id,
        "status": {"state": "failed"},
        "error": f"Unknown skill: {skill_id}",
    }
