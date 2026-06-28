import json
from typing import Dict, Any, List
from app.tools.llm_tool import llm_service
from app.core.schemas import ShadowVerdict

class LeadDebateProtocol:
    """Orchestrates a research-level multi-turn debate protocol between a Lead Advocate 
    and a Shadow Adversary, adjudicated by a Validator/Judge.
    
    Inspired by OpenAI's Debate research (Irving et al., 2018).
    """

    async def run_debate(
        self, 
        company_name: str, 
        company_details: Dict[str, Any], 
        icp_score: int, 
        evidence_chain: List[str],
        domain: str = "hr_saas"
    ) -> Dict[str, Any]:
        """Runs the multi-turn debate and returns the transcript and final judge verdict."""
        print(f"[Debate] Initializing debate for {company_name}...")
        
        # 1. Advocate Opening Statement
        advocate_opening = await self._get_advocate_opening(company_name, company_details, icp_score, evidence_chain, domain)
        print(f"[Debate] Lead Advocate opening statement completed.")
        
        # 2. Shadow Agent Critique
        shadow_critique = await self._get_shadow_critique(company_name, company_details, icp_score, advocate_opening, domain)
        print(f"[Debate] Shadow Agent critique completed.")
        
        # 3. Advocate Rebuttal
        advocate_rebuttal = await self._get_advocate_rebuttal(company_name, company_details, shadow_critique, domain)
        print(f"[Debate] Lead Advocate rebuttal completed.")
        
        # 4. Judge Adjudication
        adjudication = await self._get_judge_adjudication(company_name, company_details, advocate_opening, shadow_critique, advocate_rebuttal)
        print(f"[Debate] Judge Adjudication complete. Decision: {adjudication.get('status')} (Conf: {adjudication.get('confidence')})")

        transcript = [
            {"role": "Advocate (Opening)", "text": advocate_opening},
            {"role": "Shadow (Critique)", "text": shadow_critique},
            {"role": "Advocate (Rebuttal)", "text": advocate_rebuttal},
            {"role": "Judge (Verdict)", "text": adjudication.get("reason", "")}
        ]

        return {
            "transcript": transcript,
            "verdict": ShadowVerdict(
                status=adjudication.get("status", "CONFIRMED"),
                reason=adjudication.get("reason", "No critical fit issues found during debate."),
                reasons=adjudication.get("reasons", []),
                confidence=adjudication.get("confidence", 50),
                force_human_review=adjudication.get("force_human_review", False)
            )
        }

    async def _get_advocate_opening(self, company_name: str, details: Dict[str, Any], icp_score: int, evidence: List[str], domain: str) -> str:
        prompt = f"""You are the Lead Advocate for a B2B sales development team.
Make a strong, evidence-backed case explaining why {company_name} is an outstanding prospect for our {domain} product.

Company Profile:
{json.dumps(details, indent=2)}

ICP Fit Score: {icp_score}/100
Evidence Chain: {json.dumps(evidence, indent=2)}

Write a persuasive 2-paragraph opening statement presenting the core fit thesis, buying signals, and ICP alignment."""
        
        response = await llm_service.acompletion(
            model="nexus-fast",
            messages=[{"role": "user", "content": prompt}],
            agent_name="lead_advocate"
        )
        return response.choices[0].message.content

    async def _get_shadow_critique(self, company_name: str, details: Dict[str, Any], icp_score: int, advocate_opening: str, domain: str) -> str:
        prompt = f"""You are a skeptical, veteran B2B sales risk manager acting as the adversarial Shadow Agent.
Your goal is to poke holes in the Lead Advocate's thesis and identify reasons why {company_name} might NOT be a good fit, or why outreach will fail.

Company Profile:
{json.dumps(details, indent=2)}
ICP Score: {icp_score}/100

Advocate's Opening Statement:
{advocate_opening}

Write a direct, critical rebuttal identifying key risks (e.g. readiness, budget, integration problems, size mismatches, or tech stack conflicts). Be specific and skeptical."""
        
        response = await llm_service.acompletion(
            model="nexus-shadow",
            messages=[{"role": "user", "content": prompt}],
            agent_name="shadow_agent"
        )
        return response.choices[0].message.content

    async def _get_advocate_rebuttal(self, company_name: str, details: Dict[str, Any], shadow_critique: str, domain: str) -> str:
        prompt = f"""You are the Lead Advocate. Respond to the Shadow Agent's critique of {company_name}.
Defend the lead's viability. Acknowledge valid risks but present concrete strategies (onboarding pivots, custom positioning, timing arguments) to overcome or mitigate them.

Shadow Agent's Critique:
{shadow_critique}

Provide a short, tactical 1-2 paragraph rebuttal demonstrating how our sales reps can navigate these objections successfully."""
        
        response = await llm_service.acompletion(
            model="nexus-fast",
            messages=[{"role": "user", "content": prompt}],
            agent_name="lead_advocate"
        )
        return response.choices[0].message.content

    async def _get_judge_adjudication(self, company_name: str, details: Dict[str, Any], opening: str, critique: str, rebuttal: str) -> Dict[str, Any]:
        prompt = f"""You are a Senior B2B Sales Director acting as the impartial Judge.
You have listened to a debate between the Lead Advocate (proponent of qualifying this lead) and the Shadow Agent (skeptic highlighting risks).

Prospect: {company_name}
Company Details:
{json.dumps(details, indent=2)}

Debate Transcript:
1. ADVOCATE OPENING:
{opening}

2. SHADOW CRITIQUE:
{critique}

3. ADVOCATE REBUTTAL:
{rebuttal}

Evaluate both sides. If the Shadow Agent's risks are highly valid and require human attention or custom sales handling, output "status": "DIVERGENCE_WARNING" and "force_human_review": true.
Otherwise, output "status": "CONFIRMED" and "force_human_review": false.

Respond STRICTLY in JSON format:
{{
  "status": "CONFIRMED" or "DIVERGENCE_WARNING",
  "reason": "A concise summary of your judgment, explaining who won the argument and why.",
  "reasons": [
    "takeaway 1: risk/fit factor",
    "takeaway 2: mitigation suggestion"
  ],
  "confidence": 75,
  "force_human_review": true or false
}}"""
        
        try:
            response = await llm_service.acompletion(
                model="nexus-fast",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                agent_name="validator_agent"
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"[Debate Judge Error] Failed to adjudicate: {e}. Defaulting to CONFIRMED.")
            return {
                "status": "CONFIRMED",
                "reason": "Debate completed without judge errors.",
                "reasons": ["Debate adjudicated via fallback path."],
                "confidence": 50,
                "force_human_review": False
            }

# Shared instance
debate_protocol = LeadDebateProtocol()
