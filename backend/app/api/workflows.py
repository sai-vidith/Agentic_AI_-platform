from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from app.core.planner import planner_agent
from app.core.dag_executor import DAGExecutor
from app.core.event_store import event_store
import uuid

router = APIRouter(prefix="/v2/workflows")

from app.tools.search_tool import SearchTool
from app.tools.llm_tool import llm_service
import json

class StartWorkflowRequest(BaseModel):
    domain: str = "hr_saas"
    company_name: str

class DiscoverWorkflowRequest(BaseModel):
    domain: str = "hr_saas"
    limit: int = 3

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

@router.post("/discover")
async def discover_companies(request: DiscoverWorkflowRequest, background_tasks: BackgroundTasks):
    domain = request.domain
    limit = request.limit
    
    # Run intensive multi-angle startup discovery
    from app.tools.search_tool import discover_companies_from_web
    discovered_companies = await discover_companies_from_web(domain, limit)
            
    # Trigger the pipeline for each discovered company in the background
    for company in discovered_companies:
        background_tasks.add_task(execute_task_background, domain, company)
        
    return {
        "status": "autonomous_discovery_triggered",
        "discovered_companies": discovered_companies,
        "message": f"Triggered intensive autonomous lead generation pipelines for: {', '.join(discovered_companies)}"
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

@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str):
    lead = event_store.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    event_store.delete_lead(lead_id)
    return {"status": "success", "message": f"Successfully deleted lead {lead_id}"}

class DecryptRequest(BaseModel):
    cipher_text: str

@router.post("/decrypt")
async def decrypt_data(request: DecryptRequest):
    from app.governance.tee_layer import tee_vault
    if not request.cipher_text:
        return {"decrypted": ""}
    try:
        decrypted = tee_vault.decrypt(request.cipher_text)
        return {"decrypted": decrypted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
