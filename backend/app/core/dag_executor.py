import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.core.schemas import DAG, AgentState, WSEventTypes, LeadStatus, ProspectSummary
from app.agents import get_agent
from app.agents.base_nexus_agent import notify_agent_event
from app.core.chaos_monkey import chaos_monkey
from app.core.event_store import event_store
from app.core.memory import SharedMemory
from app.governance.attestation import attestation
from app.knowledge_graph.graph import kg_manager


class DAGExecutor:
    """Orchestrates topological task execution with mid-execution replanning,
    retry fallbacks, KG integration, and state propagation."""
    
    def __init__(self, dag: DAG):
        self.dag = dag
        self.memory = SharedMemory(session_id=uuid.uuid4().hex)
        self.token_usage = {"total_tokens": 0, "total_cost_usd": 0.0}
        self.trace_spans = []  # Observability trace spans

    async def execute(self) -> Dict[str, Any]:
        tasks = self.dag.tasks
        
        # Simple topological sort: find nodes with zero dependencies, execute them, resolve dependants
        completed = set()
        
        # Shared memory to retain context between agents
        first_task = list(tasks.values())[0] if tasks else None
        initial_company = first_task.input_data.get("company_name", "") if first_task else ""
        self.memory.update_from_agent({"company_name": initial_company})
        
        # Track remaining agents for mid-execution replanning
        remaining_agents = list(tasks.keys())
        
        while len(completed) < len(tasks):
            runnable = []
            for name, task in tasks.items():
                if name in completed:
                    continue
                # Skip agents removed by mid-execution replanning
                if name not in remaining_agents:
                    completed.add(name)
                    continue
                # If all dependencies are met (accounting for skipped deps)
                if all(dep in completed for dep in task.dependencies):
                    runnable.append(name)
                    
            if not runnable:
                # Loop detection safeguard
                break
                
            # Run runnable tasks (can be parallel if there are multiple branches)
            coroutines = [self._execute_single_task(name) for name in runnable]
            results = await asyncio.gather(*coroutines)
            
            for name, res in zip(runnable, results):
                if isinstance(res, dict):
                    self.memory.update_from_agent(res)
                completed.add(name)
                
                # --- MID-EXECUTION REPLANNING ---
                # After ICP scoring, ask the planner if we should skip downstream agents
                if name == "icp_matcher":
                    from app.core.planner import planner_agent
                    not_yet_run = [a for a in remaining_agents if a not in completed]
                    current_context = self.memory.get_context_for_agent("planner")
                    filtered = await planner_agent.replan_mid_execution(current_context, not_yet_run)
                    
                    # Log skipped agents
                    skipped = set(not_yet_run) - set(filtered)
                    for skipped_agent in skipped:
                        await notify_agent_event(
                            WSEventTypes.AGENT_COMPLETED, skipped_agent,
                            target=current_context.get("company_name"),
                            data={"skipped": True, "reason": f"Planner skipped: ICP score {current_context.get('score', 0)} below threshold"}
                        )
                    
                    remaining_agents = list(completed) + filtered
                
                # After shadow agent, replan again
                if name == "shadow_agent":
                    from app.core.planner import planner_agent
                    not_yet_run = [a for a in remaining_agents if a not in completed]
                    current_context = self.memory.get_context_for_agent("planner")
                    filtered = await planner_agent.replan_mid_execution(current_context, not_yet_run)
                    
                    # Log skipped agents
                    skipped = set(not_yet_run) - set(filtered)
                    for skipped_agent in skipped:
                        await notify_agent_event(
                            WSEventTypes.AGENT_COMPLETED, skipped_agent,
                            target=current_context.get("company_name"),
                            data={"skipped": True, "reason": "Planner skipped due to Shadow Agent divergence"}
                        )
                        
                    remaining_agents = list(completed) + filtered
                
        # --- Final output formulation ---
        final_context = self.memory.get_context_for_agent("final")
        company_name = final_context.get("company_name", "Unknown Company")
        company_details = final_context.get("company_details", {})
        contacts = final_context.get("contacts", [])
        icp_score = final_context.get("score", 0)
        evidence_chain = final_context.get("evidence_chain", [])
        outreach_template = final_context.get("outreach_template", "")
        shadow_verdict = final_context.get("shadow_verdict", None)
        is_valid = final_context.get("is_valid", True)
        
        lead_id = f"lead_{uuid.uuid4().hex[:12]}"
        
        status = LeadStatus.NEW
        if is_valid and icp_score >= 70:
            status = LeadStatus.QUALIFIED
        elif icp_score < 50:
            status = LeadStatus.DISQUALIFIED
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
            "plan_reasoning": self.dag.plan_reasoning,
            "token_usage": self.token_usage,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # --- Write lead entity to Knowledge Graph ---
        try:
            kg_manager.add_entity(company_name, "company", {
                "icp_score": icp_score,
                "status": status.value,
                "lead_id": lead_id,
            })
            # Add contact relationships
            for contact in contacts:
                contact_name = contact.get("name", "Unknown Contact")
                kg_manager.add_entity(contact_name, "person", {
                    "title": contact.get("title", ""),
                })
                kg_manager.add_relation(contact_name, company_name, "WORKS_AT")
            
            # Add company detail relationships
            if isinstance(company_details, dict):
                industry = company_details.get("industry", "")
                if industry:
                    kg_manager.add_entity(industry, "industry")
                    kg_manager.add_relation(company_name, industry, "IN_INDUSTRY")
                for tech in company_details.get("tech_stack", []):
                    kg_manager.add_entity(tech, "technology")
                    kg_manager.add_relation(company_name, tech, "USES_TECH")
        except Exception as e:
            print(f"[DAGExecutor] KG write error (non-fatal): {e}")
        
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
            "data": {"lead_id": lead_id, "score": icp_score, "plan": self.dag.plan_reasoning}
        })
        
        # Notify dashboard
        await notify_agent_event(WSEventTypes.WORKFLOW_COMPLETED, "system", target=company_name, data=lead_summary)
        
        return lead_summary

    async def _execute_single_task(self, agent_name: str) -> Dict[str, Any]:
        agent = get_agent(agent_name)
        if not agent:
            return {}
            
        task = self.dag.tasks[agent_name]
        task.status = AgentState.THINKING
        
        # Record trace span start
        span_start = datetime.now(timezone.utc)
        current_context = self.memory.get_context_for_agent(agent_name)
        await notify_agent_event(WSEventTypes.AGENT_THINKING, agent_name, target=current_context.get("company_name"))
        
        # Prepare inputs merging task templates with previous outputs
        inputs = {**task.input_data, **current_context}
        
        # --- Inject KG context into relevant agents ---
        if agent_name in ("summary_agent", "icp_matcher", "shadow_agent"):
            try:
                kg_connections = kg_manager.query_connections(current_context.get("company_name", ""))
                if kg_connections:
                    inputs["knowledge_graph_context"] = [
                        {"subject": s, "relation": r, "object": o}
                        for s, r, o in kg_connections
                    ]
            except Exception:
                pass
        
        # 1. Chaos Monkey failure injection check
        if chaos_monkey.should_fail(agent_name):
            task.status = AgentState.FAILED
            await notify_agent_event(WSEventTypes.AGENT_FAILED, agent_name, target=current_context.get("company_name"), data={"error": "Chaos Monkey error"})
            
            # Wait a moment before running retry fallback logic
            await asyncio.sleep(1.0)
            
            task.status = AgentState.RETRYING
            await notify_agent_event(WSEventTypes.AGENT_RETRYING, agent_name, target=current_context.get("company_name"), data={"msg": "Initiating fallback self-healing"})
            
            try:
                outputs = await agent.execute_with_fallback(inputs)
                task.status = AgentState.RECOVERED
                await notify_agent_event(WSEventTypes.AGENT_RECOVERED, agent_name, target=current_context.get("company_name"), data={"msg": "Self-healed from fallback cached registry."})
                self._record_span(agent_name, span_start, "recovered")
                return outputs
            except Exception as fe:
                task.status = AgentState.FAILED
                task.error_message = str(fe)
                self._record_span(agent_name, span_start, "failed")
                return {}

        # 2. Regular execution path
        try:
            outputs = await agent.execute(inputs)
            task.status = AgentState.COMPLETED
            await notify_agent_event(WSEventTypes.AGENT_COMPLETED, agent_name, target=current_context.get("company_name"), data={"output": outputs})
            self._record_span(agent_name, span_start, "completed")
            return outputs
        except Exception as e:
            # Self-healing retry fallback if live execution throws error
            task.status = AgentState.FAILED
            await notify_agent_event(WSEventTypes.AGENT_FAILED, agent_name, target=current_context.get("company_name"), data={"error": str(e)})
            
            await asyncio.sleep(1.0)
            task.status = AgentState.RETRYING
            await notify_agent_event(WSEventTypes.AGENT_RETRYING, agent_name, target=current_context.get("company_name"), data={"msg": "Self-healing: Falling back to cached data"})
            
            try:
                outputs = await agent.execute_with_fallback(inputs)
                task.status = AgentState.RECOVERED
                await notify_agent_event(WSEventTypes.AGENT_RECOVERED, agent_name, target=current_context.get("company_name"))
                self._record_span(agent_name, span_start, "recovered")
                return outputs
            except Exception as fe:
                task.status = AgentState.FAILED
                task.error_message = str(fe)
                self._record_span(agent_name, span_start, "failed")
                return {}

    def _record_span(self, agent_name: str, start_time: datetime, status: str):
        """Record an observability trace span for this agent execution."""
        end_time = datetime.now(timezone.utc)
        self.trace_spans.append({
            "agent": agent_name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_ms": int((end_time - start_time).total_seconds() * 1000),
            "status": status,
        })
