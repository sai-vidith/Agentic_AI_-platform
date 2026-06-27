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
        You are a highly skeptical B2B sales analyst. Your job is to find reasons why this company is NOT a good fit for our software.
        
        Company Profile:
        {json.dumps(company_details)}
        
        ICP Compatibility Score: {icp_score}/100
        Evidence chain: {json.dumps(evidence)}
        
        Identify the single strongest counterargument. Score your risk confidence (0-100) that this lead will turn out to be disqualified.
        Respond strictly in JSON format:
        {{
          "counter_argument": "Reason why the lead might be a bad fit...",
          "risk_confidence": 65,
          "flaw_type": "Readiness Risk / Size Mismatch / Tech Stack Conflict"
        }}
        """
        
        content = await self.call_llm(prompt, response_format={"type": "json_object"})
        data = json.loads(content)
        
        risk_conf = data.get("risk_confidence", 0)
        
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
                data={"reason": data.get("counter_argument"), "confidence": risk_conf}
            )
            
        verdict = ShadowVerdict(
            status=status,
            reason=data.get("counter_argument", ""),
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
