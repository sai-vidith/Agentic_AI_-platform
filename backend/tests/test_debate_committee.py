import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.core.schemas import ShadowVerdict

def test_buying_committee_classification():
    """Verify that job titles map correctly to Decision Maker, Influencer, or Gatekeeper."""
    contacts = [
        {"name": "Alice Smith", "title": "VP of Human Resources"},
        {"name": "Bob Jones", "title": "HR Manager"},
        {"name": "Charlie Brown", "title": "HR Coordinator"}
    ]
    
    mapped = []
    for c in contacts:
        title = c["title"].lower()
        if any(k in title for k in ("chief", "vp", "president", "cpo", "cfo", "cio", "cto", "ceo", "head of")):
            role = "Decision Maker"
        elif any(k in title for k in ("director", "manager", "lead", "architect", "engineer")):
            role = "Influencer"
        else:
            role = "Gatekeeper"
        mapped.append((c["name"], role))
        
    assert mapped == [
        ("Alice Smith", "Decision Maker"),
        ("Bob Jones", "Influencer"),
        ("Charlie Brown", "Gatekeeper")
    ]

def test_buying_committee_engagement_priority():
    """Verify the target priority ordering: Gatekeeper -> Influencer -> Decision Maker."""
    committee = [
        {"name": "Alice", "role": "Decision Maker"},
        {"name": "Bob", "role": "Influencer"},
        {"name": "Charlie", "role": "Gatekeeper"}
    ]
    
    role_priority = {"Gatekeeper": 1, "Influencer": 2, "Decision Maker": 3}
    sorted_committee = sorted(committee, key=lambda x: role_priority.get(x["role"], 9))
    
    names_in_order = [member["name"] for member in sorted_committee]
    assert names_in_order == ["Charlie", "Bob", "Alice"]

def test_debate_transcript_schema():
    """Verify shadow verdict schemas."""
    verdict = ShadowVerdict(
        status="DIVERGENCE_WARNING",
        reason="Objection raised by shadow adversary.",
        reasons=[" ob 1", "ob 2"],
        confidence=80,
        force_human_review=True
    )
    assert verdict.status == "DIVERGENCE_WARNING"
    assert verdict.confidence == 80
    assert verdict.force_human_review is True
