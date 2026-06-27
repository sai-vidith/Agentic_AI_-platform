from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from app.config import BUSINESS_CONFIG_DIR, get_business_config
import yaml
from pathlib import Path

router = APIRouter(prefix="/v2/config")

@router.get("/{domain}")
async def get_config_files(domain: str):
    try:
        return get_business_config(domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{domain}/{config_type}")
async def update_config(domain: str, config_type: str, payload: Dict[str, Any] = Body(...)):
    """Update configs (icp, personas, triggers, safety)."""
    if config_type not in ["icp", "personas", "triggers", "safety"]:
        raise HTTPException(status_code=400, detail="Invalid config type")
        
    # Map types to filenames
    if config_type == "icp":
        target_path = BUSINESS_CONFIG_DIR / "icp_profiles" / f"{domain}_icp.yaml"
    elif config_type == "personas":
        target_path = BUSINESS_CONFIG_DIR / "personas" / f"{domain}_personas.yaml"
    elif config_type == "triggers":
        target_path = BUSINESS_CONFIG_DIR / "triggers" / f"{domain}_triggers.yaml"
    else:
        target_path = BUSINESS_CONFIG_DIR / "guardrails" / "safety_policies.yaml"
        
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, default_flow_style=False)
        return {"status": "success", "message": f"Updated config for {domain}/{config_type}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")
