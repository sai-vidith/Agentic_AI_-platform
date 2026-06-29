import json
from typing import Dict, Any, List
from app.tools.llm_tool import llm_service
from app.config import get_business_config
from app.core.schemas import DAG, AgentTask

class PlannerAgent:
    """Orchestrates DYNAMIC goal decomposition, generating context-aware DAG tasks from business rules.
    
    Unlike a static pipeline, this planner uses the LLM to decide which agents
    to activate based on the target domain, company context, and business rules.
    It can skip, reorder, or add agents based on the planning output.
    """
    
    # Full agent registry with metadata for the LLM to reason about
    AGENT_REGISTRY = {
        "trigger_monitor": {
            "description": "Scans news feeds, funding databases, and job boards for business trigger events",
            "required": True,
            "stage": 1,
        },
        "company_enricher": {
            "description": "Validates and enriches company data: tech stack, employee count, funding history",
            "required": True,
            "stage": 2,
        },
        "icp_matcher": {
            "description": "Scores the company against Ideal Customer Profile criteria (0-100)",
            "required": True,
            "stage": 3,
        },
        "shadow_agent": {
            "description": "Devil's advocate — challenges high-confidence leads to find disqualifying flaws",
            "required": False,
            "stage": 4,
            "condition": "Only run if ICP score >= 70",
        },
        "persona_finder": {
            "description": "Identifies decision-makers matching target buyer personas",
            "required": False,
            "stage": 5,
            "condition": "Only run if ICP score >= 50 (skip for low-fit companies)",
        },
        "contact_enricher": {
            "description": "Enriches contact details (email, phone, LinkedIn) and applies PII/TEE protection",
            "required": False,
            "stage": 6,
            "condition": "Only run if persona_finder produced contacts",
        },
        "summary_agent": {
            "description": "Generates actionable outreach recommendation with evidence chain",
            "required": False,
            "stage": 7,
            "condition": "Only run if lead is qualified (ICP >= 50)",
        },
        "validator_agent": {
            "description": "Final quality check — validates output completeness and detects hallucinations",
            "required": True,
            "stage": 8,
        },
    }
    
    def __init__(self):
        pass

    async def create_plan(self, domain: str, company_name: str) -> DAG:
        """Dynamically generates an execution DAG using LLM reasoning + business rules."""
        biz_config = get_business_config(domain)
        
        # Ask the LLM to decide which agents to activate and in what order
        agent_descriptions = "\n".join([
            f"- {name}: {info['description']} | Required: {info['required']} | Condition: {info.get('condition', 'Always run')}"
            for name, info in self.AGENT_REGISTRY.items()
        ])
        
        prompt = f"""You are an AI orchestration planner for B2B lead qualification.

Target Domain: {domain}
Target Company: {company_name}

Available Agents:
{agent_descriptions}

Business Configuration:
{json.dumps(biz_config, indent=2, default=str)}

Based on the target domain and company, decide which agents to activate.
Return a JSON object with:
- "active_agents": list of agent names to run, in execution order
- "reasoning": brief explanation of your plan
- "skip_reasons": dict mapping skipped agent names to reasons

Rules:
1. Required agents (trigger_monitor, company_enricher, icp_matcher, validator_agent) MUST always be included.
2. Optional agents can be skipped based on domain context.
3. For unknown companies, include ALL agents to gather maximum intelligence.
4. For well-known companies, you may skip trigger_monitor.
5. Maintain logical ordering: enrichment before scoring, scoring before persona matching.

Respond strictly in JSON format."""

        # Default full pipeline (used if LLM call fails)
        default_agents = list(self.AGENT_REGISTRY.keys())
        active_agents = default_agents
        plan_reasoning = "Default sequential pipeline"
        
        try:
            response = await llm_service.acompletion(
                model="nexus-fast",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            plan_data = json.loads(content)
            
            proposed_agents = plan_data.get("active_agents", default_agents)
            plan_reasoning = plan_data.get("reasoning", "LLM-optimized plan")
            
            # Validate: ensure required agents are always present
            required = [name for name, info in self.AGENT_REGISTRY.items() if info["required"]]
            for req in required:
                if req not in proposed_agents:
                    proposed_agents.append(req)
            
            # Re-sort by stage order to maintain logical flow
            proposed_agents = sorted(
                proposed_agents,
                key=lambda a: self.AGENT_REGISTRY.get(a, {}).get("stage", 99)
            )
            
            active_agents = proposed_agents
            try:
                print(f"[Planner] LLM Plan: {plan_reasoning}")
                print(f"[Planner] Active agents: {active_agents}")
                if "skip_reasons" in plan_data:
                    for agent, reason in plan_data["skip_reasons"].items():
                        print(f"[Planner] Skipped {agent}: {reason}")
            except Exception as pe:
                pass
                    
        except Exception as e:
            try:
                print(f"[Planner] LLM planning failed ({e}), using default pipeline")
            except Exception:
                print("[Planner] LLM planning failed (encoding error on print), using default pipeline")
        
        # Build the DAG from the active agent list
        tasks = {}
        for idx, name in enumerate(active_agents):
            dependencies = [active_agents[idx - 1]] if idx > 0 else []
            tasks[name] = AgentTask(
                id=name,
                name=name,
                dependencies=dependencies,
                input_data={
                    "domain": domain,
                    "company_name": company_name,
                    "icp_rules": biz_config.get("icp") if name == "icp_matcher" else {},
                    "persona_rules": biz_config.get("personas") if name == "persona_finder" else {},
                    "trigger_rules": biz_config.get("triggers") if name == "trigger_monitor" else {}
                }
            )
            
        edges = []
        for i, name in enumerate(active_agents[1:], 1):
            edges.append([active_agents[i - 1], name])

        return DAG(tasks=tasks, edges=edges, plan_reasoning=plan_reasoning)

    async def replan_mid_execution(self, current_context: Dict[str, Any], remaining_agents: List[str]) -> List[str]:
        """Mid-execution replanning: dynamically drop agents if intermediate results indicate low fit.
        
        Called by DAGExecutor after ICP scoring to conditionally skip downstream agents.
        """
        icp_score = current_context.get("score", 0)
        shadow_verdict = current_context.get("shadow_verdict", {})
        
        filtered = []
        skip_reasons = []
        
        for agent_name in remaining_agents:
            info = self.AGENT_REGISTRY.get(agent_name, {})
            
            # Skip persona/contact/summary for very low ICP scores
            if agent_name in ("persona_finder", "contact_enricher", "summary_agent") and icp_score < 50:
                skip_reasons.append(f"Skipping {agent_name}: ICP score {icp_score} < 50 threshold")
                continue
            
            # Skip shadow_agent for low-confidence leads (not worth challenging)
            if agent_name == "shadow_agent" and icp_score < 70:
                skip_reasons.append(f"Skipping shadow_agent: ICP score {icp_score} < 70 (not worth challenging)")
                continue
            
            # Skip contact_enricher if shadow agent issued a hard rejection
            if agent_name == "contact_enricher" and shadow_verdict.get("status") == "DIVERGENCE_WARNING":
                if shadow_verdict.get("confidence", 0) > 80:
                    skip_reasons.append(f"Skipping contact_enricher: Shadow agent high-confidence rejection ({shadow_verdict.get('confidence')})")
                    continue
            
            filtered.append(agent_name)
        
        for reason in skip_reasons:
            print(f"[Planner:Replan] {reason}")
        
        return filtered


# Shared planner
planner_agent = PlannerAgent()
