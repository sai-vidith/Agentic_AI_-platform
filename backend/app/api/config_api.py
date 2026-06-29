from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from app.config import BUSINESS_CONFIG_DIR, get_business_config, BASE_DIR
import yaml
import json
from pathlib import Path
import os

router = APIRouter(prefix="/v2/config")

@router.get("/domains/list")
async def list_domains():
    """List all available domains discovered from YAML profiles."""
    domains = ["hr_saas", "cybersecurity"]
    icp_dir = BUSINESS_CONFIG_DIR / "icp_profiles"
    if icp_dir.exists():
        for filename in os.listdir(icp_dir):
            if filename.endswith("_icp.yaml"):
                dom = filename.replace("_icp.yaml", "")
                if dom not in domains:
                    domains.append(dom)
    return domains

@router.post("/domains/create")
async def create_domain(payload: Dict[str, Any] = Body(...)):
    """Create a new domain with default YAML files and default empty mock_data.json."""
    domain = payload.get("domain", "").strip().lower().replace(" ", "_")
    if not domain:
        raise HTTPException(status_code=400, detail="Missing or invalid domain name")
        
    icp_path = BUSINESS_CONFIG_DIR / "icp_profiles" / f"{domain}_icp.yaml"
    personas_path = BUSINESS_CONFIG_DIR / "personas" / f"{domain}_personas.yaml"
    triggers_path = BUSINESS_CONFIG_DIR / "triggers" / f"{domain}_triggers.yaml"
    mock_path = BASE_DIR / "app" / "mock_data" / f"{domain}_mock.json"
    
    # 1. Default ICP
    default_icp = {
        "domain": domain,
        "description": f"Custom ICP configuration for {domain}",
        "min_employees": 10,
        "max_employees": 1000,
        "target_industries": ["Software", "SaaS", "Fintech"],
        "target_regions": ["US", "India", "Europe"],
        "growth_criteria": {
            "min_growth_rate": "15% headcount growth",
            "min_job_postings": 2
        },
        "tech_stack_preference": ["GitHub", "Slack"],
        "disqualifying_signals": ["declining headcount"],
        "icp_weighting": {
            "employees": 0.2,
            "industry": 0.2,
            "growth": 0.3,
            "tech_stack": 0.1,
            "triggers": 0.2
        }
    }
    
    # 2. Default Personas
    default_personas = {
        "domain": domain,
        "personas": [
            {
                "id": "decision_maker",
                "title_patterns": ["Founder", "CEO", "VP of Operations", "Director"],
                "priority": 1,
                "description": "Primary decision maker"
            }
        ]
    }
    
    # 3. Default Triggers
    default_triggers = {
        "domain": domain,
        "triggers": [
            {
                "id": "funding_alert",
                "type": "funding",
                "keywords": ["raises round", "funding", "secured investment"],
                "score_boost": 20,
                "description": "Signals capital influx and scaling needs"
            }
        ]
    }
    
    # 4. Default mock data template
    default_mock = [
        {
            "name": "Custom Alpha Corp",
            "industry": "Software",
            "employees": 75,
            "founded": 2023,
            "hq": "San Francisco, US",
            "tech_stack": ["React", "AWS", "GitHub", "Slack"],
            "current_hr_tool": "Excel",
            "recent_funding": {"round": "Series A", "amount_usd": 12000000, "date": "2026-06-01"},
            "growth_rate": "35% headcount growth",
            "contacts": [
                {
                    "name": "Alex Mercer",
                    "title": "Director of Technology",
                    "email": "alex.mercer@customalphacorp.com",
                    "phone": "+1-555-0145",
                    "linkedin": "https://linkedin.com/in/alexmercer-customalphacorp"
                }
            ]
        }
    ]
    
    try:
        icp_path.parent.mkdir(parents=True, exist_ok=True)
        personas_path.parent.mkdir(parents=True, exist_ok=True)
        triggers_path.parent.mkdir(parents=True, exist_ok=True)
        mock_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(icp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_icp, f, default_flow_style=False)
        with open(personas_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_personas, f, default_flow_style=False)
        with open(triggers_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_triggers, f, default_flow_style=False)
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(default_mock, f, indent=2)
            
        return {"status": "success", "message": f"Successfully created new domain '{domain}' with templates."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create domain files: {e}")

@router.get("/{domain}/mock-data")
async def get_mock_data(domain: str):
    """Retrieve mock JSON dataset for this domain."""
    mock_path = BASE_DIR / "app" / "mock_data" / f"{domain}_mock.json"
    if not mock_path.exists():
        # Fallback to general companies.json if custom domain mock doesn't exist
        mock_path = BASE_DIR / "app" / "mock_data" / "companies.json"
        
    try:
        with open(mock_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read mock file: {e}")

@router.post("/{domain}/mock-data")
async def save_mock_data(domain: str, payload: List[Dict[str, Any]] = Body(...)):
    """Save custom mock companies & contacts JSON file for this domain."""
    mock_path = BASE_DIR / "app" / "mock_data" / f"{domain}_mock.json"
    try:
        mock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mock_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return {"status": "success", "message": f"Saved custom mock file for {domain}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save mock file: {e}")

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
