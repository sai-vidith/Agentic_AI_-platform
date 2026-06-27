from fastapi import APIRouter
from app.agents import agent_registry

router = APIRouter(prefix="/v2/agents")

@router.get("")
async def list_agents():
    agents_list = []
    for name, agent in agent_registry.items():
        agents_list.append({
            "name": name,
            "model": agent.model,
            "description": agent.__doc__ or "Specialist NexusAI agent"
        })
    return agents_list
