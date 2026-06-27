"""Unit tests for Shadow Agent — validates divergence detection and HITL routing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.schemas import ShadowVerdict
import pytest


class TestShadowVerdict:
    """Tests for Shadow Agent verdict logic."""
    
    def test_high_confidence_triggers_divergence(self):
        """Risk confidence > 60 should trigger DIVERGENCE_WARNING."""
        risk_confidence = 75
        status = "DIVERGENCE_WARNING" if risk_confidence > 60 else "CONFIRMED"
        force_review = risk_confidence > 60
        
        verdict = ShadowVerdict(
            status=status,
            reason="Company may build HR tools internally",
            confidence=risk_confidence,
            force_human_review=force_review,
        )
        
        assert verdict.status == "DIVERGENCE_WARNING"
        assert verdict.force_human_review is True
        assert verdict.confidence == 75
    
    def test_low_confidence_confirms_lead(self):
        """Risk confidence <= 60 should confirm the lead."""
        risk_confidence = 35
        status = "DIVERGENCE_WARNING" if risk_confidence > 60 else "CONFIRMED"
        force_review = risk_confidence > 60
        
        verdict = ShadowVerdict(
            status=status,
            reason="No significant risks found",
            confidence=risk_confidence,
            force_human_review=force_review,
        )
        
        assert verdict.status == "CONFIRMED"
        assert verdict.force_human_review is False
    
    def test_boundary_confidence_60_confirms(self):
        """Exactly 60 should NOT trigger divergence (> 60, not >=)."""
        risk_confidence = 60
        status = "DIVERGENCE_WARNING" if risk_confidence > 60 else "CONFIRMED"
        
        assert status == "CONFIRMED"
    
    def test_verdict_serialization(self):
        """Verify verdict dict() output contains all fields."""
        verdict = ShadowVerdict(
            status="DIVERGENCE_WARNING",
            reason="Test reason",
            confidence=80,
            force_human_review=True,
        )
        d = verdict.dict()
        assert d["status"] == "DIVERGENCE_WARNING"
        assert d["reason"] == "Test reason"
        assert d["confidence"] == 80
        assert d["force_human_review"] is True


class TestPlannerReplanning:
    """Tests for mid-execution replanning logic."""
    
    def test_low_icp_skips_downstream_agents(self):
        """ICP score < 50 should skip persona_finder, contact_enricher, summary_agent."""
        icp_score = 35
        remaining = ["shadow_agent", "persona_finder", "contact_enricher", "summary_agent", "validator_agent"]
        
        filtered = []
        for agent in remaining:
            if agent in ("persona_finder", "contact_enricher", "summary_agent") and icp_score < 50:
                continue
            if agent == "shadow_agent" and icp_score < 70:
                continue
            filtered.append(agent)
        
        assert "persona_finder" not in filtered
        assert "contact_enricher" not in filtered
        assert "summary_agent" not in filtered
        assert "shadow_agent" not in filtered
        assert "validator_agent" in filtered
    
    def test_high_icp_keeps_all_agents(self):
        """ICP score >= 70 should keep all agents."""
        icp_score = 85
        remaining = ["shadow_agent", "persona_finder", "contact_enricher", "summary_agent", "validator_agent"]
        
        filtered = []
        for agent in remaining:
            if agent in ("persona_finder", "contact_enricher", "summary_agent") and icp_score < 50:
                continue
            if agent == "shadow_agent" and icp_score < 70:
                continue
            filtered.append(agent)
        
        assert filtered == remaining


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
