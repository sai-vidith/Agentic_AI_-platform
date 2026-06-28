import json
from typing import Dict, Any
from app.agents.base_nexus_agent import BaseNexusAgent, notify_agent_event
from app.core.schemas import WSEventTypes, ShadowVerdict

class ShadowAgent(BaseNexusAgent):
    """Devil's advocate agent that challenges high-confidence leads to find flaws."""
    
    def __init__(self):
        super().__init__(name="shadow_agent", model="nexus-shadow")

    async def execute(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        company_details = task_input.get("company_details", {})
        company_name = company_details.get("name", "Unknown Company")
        icp_score = task_input.get("icp_score", 0)
        evidence = task_input.get("evidence_chain", [])
        
        prompt = f"""
        You are a highly skeptical veteran B2B sales analyst and risk manager with 15+ years of experience dealing with thousands of customers.
        Your job is to identify multiple potential risks or reasons why this company might NOT be a good fit, or where our outreach strategy might fail, and check data integrity.
        
        Veteran Sales Rep Insights:
        - Analyze hiring signals carefully. If they have posted a job and the position is recently fulfilled:
          * A novice might think they don't need us anymore.
          * A veteran knows they now have an urgent need for onboarding, payroll, retention, and performance management for the new hire. If they lack modern HR SaaS, manual setup increases early turnover risk.
          * A fulfilled job is a positive sign of budget and growth, not a reason to disqualify. However, a pitch focused only on recruiting/ATS will fail; we must pivot to employee management and onboarding SaaS.
          * Check if there's a risk of outreach timing (they might have temporary breathing room, but their admin burden is peaking).
        
        Company Profile:
        {json.dumps(company_details)}
        
        ICP Compatibility Score: {icp_score}/100
        Evidence chain: {json.dumps(evidence)}
        
        Identify ALL potential risks (Tech Stack Conflict, Readiness Risk, Size Mismatch, Data Integrity, Sales Cycle Timing, or Job Fulfillment Pivot).
        Score your risk confidence (0-100) that this lead requires human review or customized positioning before outreach.
        
        Respond strictly in JSON format:
        {{
          "counter_argument": "A primary summary of the risk or outreach pivot required",
          "reasons": [
            "Reason 1: Specific detail about size/stack/timing/fulfillment",
            "Reason 2: Detail about another risk factor",
            "Reason 3: Detail about how the fulfilled job affects their SaaS readiness/needs"
          ],
          "risk_confidence": 75,
          "flaw_type": "Readiness Risk / Size Mismatch / Tech Stack Conflict / Data Integrity Risk / Timing Pivot"
        }}
        """
        
        content = await self.call_llm(prompt, response_format={"type": "json_object"})
        data = json.loads(content)
        
        risk_conf = data.get("risk_confidence", 0)
        reasons_list = data.get("reasons", [data.get("counter_argument", "")]) if data.get("reasons") else [data.get("counter_argument", "")]
        
        # Trigger WS event if high divergence
        status = "CONFIRMED"
        force_review = False
        if risk_conf > 60:
            status = "DIVERGENCE_WARNING"
            force_review = True
            await notify_agent_event(
                WSEventTypes.SHADOW_DIVERGENCE, 
                self.name, 
                target=company_name, 
                data={"reason": data.get("counter_argument"), "reasons": reasons_list, "confidence": risk_conf}
            )
            
        verdict = ShadowVerdict(
            status=status,
            reason=data.get("counter_argument", ""),
            reasons=reasons_list,
            confidence=risk_conf,
            force_human_review=force_review
        )
        
        await notify_agent_event(WSEventTypes.AGENT_COMPLETED, self.name, target=company_name, data={"output": verdict.dict()})
        return {"shadow_verdict": verdict.dict()}

    async def execute_with_fallback(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        verdict = ShadowVerdict(
            status="CONFIRMED",
            reason="No critical risk indicators flagged.",
            confidence=20,
            force_human_review=False
        )
        return {"shadow_verdict": verdict.dict()}
