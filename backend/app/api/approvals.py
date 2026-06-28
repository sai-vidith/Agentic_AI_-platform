from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from app.core.event_store import event_store
from app.core.schemas import LeadStatus

router = APIRouter(prefix="/v2/approvals")

@router.get("/queue")
async def get_approval_queue():
    leads = event_store.get_all_leads()
    # Filter approvals
    queue = [l for l in leads if l.get("status") == LeadStatus.APPROVAL_REQUIRED.value]
    return queue

@router.post("/{lead_id}/action")
async def action_lead(
    lead_id: str,
    action: str = Body(..., embed=True),  # "approve" or "reject"
    outreach_template: str = Body(None, embed=True)
):
    lead = event_store.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    if action == "approve":
        lead["status"] = LeadStatus.APPROVED.value
    elif action == "reject":
        lead["status"] = LeadStatus.REJECTED.value
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'approve' or 'reject'.")
        
    if outreach_template:
        lead["outreach_template"] = outreach_template
        
    event_store.save_lead(lead)
    
    # Record learning feedback signal for reinforcement
    try:
        from app.core.feedback import feedback_manager
        feedback_manager.record_feedback(lead, action)
    except Exception as ex:
        print(f"[FeedbackManager] Error recording action feedback: {ex}")
    
    # Log audit event
    event_store.log_event({
        "source": "governance_approvals",
        "event_type": f"lead_{action}d",
        "company": lead.get("company_name"),
        "data": {"lead_id": lead_id, "outreach_edited": outreach_template is not None}
    })
    
    return {"status": "success", "lead_status": lead["status"]}
