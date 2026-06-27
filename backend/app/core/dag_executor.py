import asyncio
from datetime import datetime
from typing import Dict, Any, List
from app.core.schemas import DAG, AgentState, WSEventTypes, LeadStatus, ProspectSummary
from app.agents import get_agent
from app.agents.base_nexus_agent import notify_agent_event
from app.core.chaos_monkey import chaos_monkey
from app.core.event_store import event_store
from app.governance.attestation import attestation

class DAGExecutor:
    """Orchestrates topological task execution, retry fallbacks, and state propagation."""
    
    def __init__(self, dag: DAG):
        self.dag = dag
        self.run_data = {} # Shared runtime state between agents

    async def execute(self) -> Dict[str, Any]:
        tasks = self.dag.tasks
        
        # Simple topological sort (since it's mostly sequential in this pipeline)
        # We find nodes with zero dependencies, execute them, resolve their dependants, etc.
        completed = set()
        
        # Shared context dictionary passed along from agent to agent
        first_task = list(tasks.values())[0] if tasks else None
        initial_company = first_task.input_data.get("company_name", "") if first_task else ""
        context = {"company_name": initial_company}
        
        while len(completed) < len(tasks):
            runnable = []
            for name, task in tasks.items():
                if name in completed:
                    continue
                # If all dependencies are met
                if all(dep in completed for dep in task.dependencies):
                    runnable.append(name)
                    
            if not runnable:
                # Loop detection safeguard
                break
                
            # Run runnable tasks (can be parallel if there are multiple branches)
            coroutines = [self._execute_single_task(name, context) for name in runnable]
            results = await asyncio.gather(*coroutines)
            
            for name, res in zip(runnable, results):
                context.update(res)
                completed.add(name)
                
        # Final output formulation
        # 1. Store lead in database
        company_name = context.get("company_name", "Unknown Company")
        company_details = context.get("company_details", {})
        contacts = context.get("contacts", [])
        icp_score = context.get("score", 0)
        evidence_chain = context.get("evidence_chain", [])
        outreach_template = context.get("outreach_template", "")
        shadow_verdict = context.get("shadow_verdict", None)
        is_valid = context.get("is_valid", True)
        
        lead_id = f"lead_{int(asyncio.get_event_loop().time())}"
        
        status = LeadStatus.NEW
        if is_valid and icp_score >= 70:
            status = LeadStatus.QUALIFIED
        if shadow_verdict and shadow_verdict.get("status") == "DIVERGENCE_WARNING":
            status = LeadStatus.APPROVAL_REQUIRED
            
        lead_summary = {
            "id": lead_id,
            "company_name": company_name,
            "company_details": company_details,
            "contacts": contacts,
            "icp_score": icp_score,
            "evidence_chain": evidence_chain,
            "shadow_verdict": shadow_verdict,
            "outreach_template": outreach_template,
            "status": status.value,
            "created_at": datetime.utcnow() if hasattr(datetime, "utcnow") else None
        }
        
        # Run TEE Attestation audit signing
        attest_report = attestation.generate_attestation_report(
            lead_id,
            company_name,
            icp_score,
            is_valid
        )
        lead_summary["attestation"] = attest_report
        
        # Save to database
        event_store.save_lead(lead_summary)
        
        # Log event
        event_store.log_event({
            "source": "workflow_engine",
            "event_type": "lead_discovered",
            "company": company_name,
            "data": {"lead_id": lead_id, "score": icp_score}
        })
        
        # Notify dashboard
        await notify_agent_event(WSEventTypes.WORKFLOW_COMPLETED, "system", target=company_name, data=lead_summary)
        
        return lead_summary

    async def _execute_single_task(self, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        agent = get_agent(agent_name)
        if not agent:
            return {}
            
        task = self.dag.tasks[agent_name]
        task.status = AgentState.THINKING
        await notify_agent_event(WSEventTypes.AGENT_THINKING, agent_name, target=context.get("company_name"))
        
        # Prepare inputs merging task templates with previous outputs
        inputs = {**task.input_data, **context}
        
        # 1. Chaos Monkey failure injection check
        if chaos_monkey.should_fail(agent_name):
            task.status = AgentState.FAILED
            await notify_agent_event(WSEventTypes.AGENT_FAILED, agent_name, target=context.get("company_name"), data={"error": "Chaos Monkey error"})
            
            # Wait a moment before running retry fallback logic
            await asyncio.sleep(1.0)
            
            task.status = AgentState.RETRYING
            await notify_agent_event(WSEventTypes.AGENT_RETRYING, agent_name, target=context.get("company_name"), data={"msg": "Initiating fallback self-healing"})
            
            try:
                outputs = await agent.execute_with_fallback(inputs)
                task.status = AgentState.RECOVERED
                await notify_agent_event(WSEventTypes.AGENT_RECOVERED, agent_name, target=context.get("company_name"), data={"msg": "Self-healed from fallback cached registry."})
                return outputs
            except Exception as fe:
                task.status = AgentState.FAILED
                task.error_message = str(fe)
                return {}

        # 2. Regular execution path
        try:
            outputs = await agent.execute(inputs)
            task.status = AgentState.COMPLETED
            await notify_agent_event(WSEventTypes.AGENT_COMPLETED, agent_name, target=context.get("company_name"), data={"output": outputs})
            return outputs
        except Exception as e:
            # Self-healing retry fallback if live execution throws error
            task.status = AgentState.FAILED
            await notify_agent_event(WSEventTypes.AGENT_FAILED, agent_name, target=context.get("company_name"), data={"error": str(e)})
            
            await asyncio.sleep(1.0)
            task.status = AgentState.RETRYING
            await notify_agent_event(WSEventTypes.AGENT_RETRYING, agent_name, target=context.get("company_name"), data={"msg": "Self-healing: Falling back to cached data"})
            
            try:
                outputs = await agent.execute_with_fallback(inputs)
                task.status = AgentState.RECOVERED
                await notify_agent_event(WSEventTypes.AGENT_RECOVERED, agent_name, target=context.get("company_name"))
                return outputs
            except Exception as fe:
                task.status = AgentState.FAILED
                task.error_message = str(fe)
                return {}
