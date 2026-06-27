from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.core.event_store import event_store
from app.core.planner import planner_agent
from app.core.dag_executor import DAGExecutor

router = APIRouter(prefix="/v2/webhooks")

class WebhookPayload(BaseModel):
    source: str          # "crunchbase", "linkedin", "custom"
    event_type: str      # "funding", "hiring", "leadership_change"
    company: str
    data: Dict[str, Any]

async def process_webhook_lead(company_name: str):
    try:
        dag = await planner_agent.create_plan("hr_saas", company_name)
        executor = DAGExecutor(dag)
        await executor.execute()
    except Exception as e:
        print(f"Webhook lead process failed: {e}")

@router.post("/{source}")
async def receive_webhook(
    source: str,
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    x_webhook_secret: Optional[str] = Header(None)
):
    # Log incoming event in event store
    event_store.log_event({
        "source": source,
        "event_type": payload.event_type,
        "company": payload.company,
        "data": payload.data
    })
    
    # Run pipeline in background
    background_tasks.add_task(process_webhook_lead, payload.company)
    
    return {
        "status": "accepted",
        "event": payload.event_type,
        "target": payload.company
    }
