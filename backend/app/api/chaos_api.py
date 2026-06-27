from fastapi import APIRouter, Body
from app.core.chaos_monkey import chaos_monkey

router = APIRouter(prefix="/v2/chaos")

@router.get("/status")
async def get_chaos_status():
    return {
        "enabled": chaos_monkey.enabled,
        "failure_targets": chaos_monkey.failure_targets
    }

@router.post("/toggle")
async def toggle_chaos(enabled: bool = Body(..., embed=True)):
    chaos_monkey.toggle(enabled)
    return {
        "status": "success",
        "enabled": chaos_monkey.enabled,
        "message": f"Chaos Monkey is now {'ENABLED' if enabled else 'DISABLED'}"
    }
