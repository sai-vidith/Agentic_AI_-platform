from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from app.core.planner import planner_agent
from app.core.dag_executor import DAGExecutor
from app.core.event_store import event_store
import uuid

router = APIRouter(prefix="/v2/workflows")

class StartWorkflowRequest(BaseModel):
    domain: str = "hr_saas"
    company_name: str

async def execute_task_background(domain: str, company_name: str):
    try:
        dag = await planner_agent.create_plan(domain, company_name)
        executor = DAGExecutor(dag)
        await executor.execute()
    except Exception as e:
        print(f"Background execution failed: {e}")

@router.post("/run")
async def run_workflow(request: StartWorkflowRequest, background_tasks: BackgroundTasks):
    company = request.company_name.strip()
    if not company:
        raise HTTPException(status_code=400, detail="Company name is required")
        
    # Launch in background to prevent request timing out
    background_tasks.add_task(execute_task_background, request.domain, company)
    
    return {
        "status": "triggered",
        "message": f"Workflow run initiated for target: {company}",
        "domain": request.domain
    }

@router.get("/leads")
async def get_discovered_leads():
    return event_store.get_all_leads()

@router.get("/leads/{lead_id}")
async def get_lead_details(lead_id: str):
    lead = event_store.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
