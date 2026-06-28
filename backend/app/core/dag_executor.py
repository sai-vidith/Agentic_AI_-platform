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
            
        # Collect sources
        sources = []
        # 1. Company website
        website = None
        if isinstance(company_details, dict):
            website = company_details.get("website")
        if not website:
            website = f"https://www.{company_name.lower().replace(' ', '')}.com"
        sources.append({"title": f"{company_name} Website", "url": website})
        
        # 2. LinkedIn contacts
        for contact in contacts:
            linkedin = contact.get("linkedin")
            if linkedin:
                url = linkedin if linkedin.startswith("http") else f"https://{linkedin}"
                sources.append({"title": f"{contact.get('name')} (LinkedIn)", "url": url})
                
        # 3. News articles
        articles = final_context.get("articles", [])
        for article in articles:
            url = article.get("url")
            if url:
                sources.append({"title": f"News: {article.get('title')} ({article.get('source')})", "url": url})

        # Check if the company has already been qualified/processed
        existing_lead = event_store.get_lead_by_company(company_name)
        if existing_lead:
            # Silently merge and search for new contacts
            existing_contacts = existing_lead.get("contacts", [])
            existing_names = {c.get("name", "").strip().lower() for c in existing_contacts if c.get("name")}
            existing_lis = {c.get("linkedin", "").strip().lower() for c in existing_contacts if c.get("linkedin")}
            
            new_contacts_added = []
            for c in contacts:
                name = c.get("name", "").strip().lower()
                li = c.get("linkedin", "").strip().lower()
                if (name and name not in existing_names) and (not li or li not in existing_lis):
                    existing_contacts.append(c)
                    new_contacts_added.append(c)
                    
            existing_sources = existing_lead.get("sources", [])
            existing_urls = {s.get("url", "").strip().lower() for s in existing_sources if s.get("url")}
            for s in sources:
                url = s.get("url", "").strip().lower()
                if url and url not in existing_urls:
                    existing_sources.append(s)
                    
            existing_lead["contacts"] = existing_contacts
            existing_lead["sources"] = existing_sources
            
            # Save the updated lead silently
            event_store.save_lead(existing_lead)
            
            # Log silent update event
            event_store.log_event({
                "source": "workflow_engine",
                "event_type": "lead_contacts_updated",
                "company": company_name,
                "data": {
                    "lead_id": existing_lead["id"],
                    "new_contacts_found": len(new_contacts_added),
                    "total_contacts": len(existing_contacts)
                }
            })
            
            # Send Email and WS updates
            if new_contacts_added:
                try:
                    from app.observability.notifier import notifier
                    subject = f"👥 [NexusAI] New Contacts Discovered for {company_name}"
                    contacts_list_html = "".join([
                        f"<li><strong>{c.get('name')}</strong> - {c.get('title') or 'Executive'}</li>"
                        for c in new_contacts_added
                    ])
                    html_body = f"""
                    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
                        <h2 style="color: #06b6d4; margin-top: 0; font-family: system-ui, -apple-system, sans-serif;">👥 New Decision Makers Identified</h2>
                        <p style="font-size: 14px; color: #334155; line-height: 1.5; font-family: system-ui, -apple-system, sans-serif;">
                            While scanning <strong>{company_name}</strong>, our research agents identified the following new decision maker profiles:
                        </p>
                        <ul style="font-size: 13px; color: #334155; line-height: 1.6;">
                            {contacts_list_html}
                        </ul>
                        <div style="margin: 20px 0; text-align: center;">
                            <a href="http://localhost:3000/leads" style="display: inline-block; padding: 10px 20px; background-color: #06b6d4; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; font-family: system-ui, -apple-system, sans-serif;">View Lead Details</a>
                        </div>
                    </div>
                    """
                    notifier.send_notification(subject, html_body)
                except Exception as e:
                    print(f"[Notifier] New contacts alert send failed: {e}")
                    
                await notify_agent_event(
                    "lead_contacts_updated", 
                    "system", 
                    target=company_name, 
                    data={"new_contacts_count": len(new_contacts_added), "total_contacts": len(existing_contacts)}
                )
            else:
                await notify_agent_event(
                    "lead_scanned_no_change", 
                    "system", 
                    target=company_name, 
                    data={"message": f"Company {company_name} scanned silently. No new contacts found."}
                )
                
            return existing_lead

        lead_summary = {
            "id": lead_id,
            "company_name": company_name,
            "company_details": company_details,
            "contacts": contacts,
            "icp_score": icp_score,
            "evidence_chain": evidence_chain,
            "shadow_verdict": shadow_verdict,
            "sources": sources,
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
        
        # Trigger Email Notification (Option 1: Free SMTP or Resend API)
        if status.value == LeadStatus.APPROVAL_REQUIRED.value:
            try:
                from app.observability.notifier import notifier
                subject = f"⚠️ [NexusAI] Approval Required: New Lead Flagged - {company_name}"
                html_body = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
                    <h2 style="color: #d97706; margin-top: 0; font-family: system-ui, -apple-system, sans-serif;">⚠️ Action Required: Human Approval Needed</h2>
                    <p style="font-size: 14px; color: #334155; line-height: 1.5; font-family: system-ui, -apple-system, sans-serif;">
                        The adversarial Shadow Agent has flagged a potential fit divergence or readiness risk for <strong>{company_name}</strong>.
                    </p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; font-family: monospace;">
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 8px 0; font-weight: bold; color: #475569;">ICP Score:</td>
                            <td style="padding: 8px 0; color: #0f172a;">{icp_score}/100</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 8px 0; font-weight: bold; color: #475569;">Risk Factor:</td>
                            <td style="padding: 8px 0; color: #d97706; font-weight: bold;">{shadow_verdict.get('confidence', '75') if shadow_verdict else '75'}%</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 8px 0; font-weight: bold; color: #475569;">Primary Flaw:</td>
                            <td style="padding: 8px 0; color: #0f172a;">{shadow_verdict.get('reason', 'N/A') if shadow_verdict else 'N/A'}</td>
                        </tr>
                    </table>
                    <div style="margin: 20px 0; text-align: center;">
                        <a href="http://localhost:5173/approvals" style="display: inline-block; padding: 10px 20px; background-color: #d97706; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; font-family: system-ui, -apple-system, sans-serif;">Go to Approvals Dashboard</a>
                    </div>
                    <p style="font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 10px; margin-top: 15px; font-family: system-ui, -apple-system, sans-serif;">
                        This notification was generated automatically by NexusAI Platform Core.
                    </p>
                </div>
                """
                notifier.send_notification(subject, html_body)
            except Exception as e:
                print(f"[Notifier] Approval alert send failed: {e}")
        elif status.value == LeadStatus.QUALIFIED.value:
            try:
                from app.observability.notifier import notifier
                subject = f"🚀 [NexusAI] New Qualified Lead Discovered: {company_name}"
                html_body = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
                    <h2 style="color: #10b981; margin-top: 0; font-family: system-ui, -apple-system, sans-serif;">🚀 Qualified Lead Discovered</h2>
                    <p style="font-size: 14px; color: #334155; line-height: 1.5; font-family: system-ui, -apple-system, sans-serif;">
                        A new B2B prospect matching target ICP guidelines has been successfully qualified for <strong>{company_name}</strong>.
                    </p>
                    <table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; font-family: monospace;">
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 8px 0; font-weight: bold; color: #475569;">ICP Score:</td>
                            <td style="padding: 8px 0; color: #10b981; font-weight: bold;">{icp_score}/100</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 8px 0; font-weight: bold; color: #475569;">Industry:</td>
                            <td style="padding: 8px 0; color: #0f172a;">{company_details.get('industry', 'N/A') if isinstance(company_details, dict) else 'N/A'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 8px 0; font-weight: bold; color: #475569;">Employees:</td>
                            <td style="padding: 8px 0; color: #0f172a;">{company_details.get('employees', 'N/A') if isinstance(company_details, dict) else 'N/A'}</td>
                        </tr>
                    </table>
                    <div style="margin: 20px 0; text-align: center;">
                        <a href="http://localhost:5173/leads" style="display: inline-block; padding: 10px 20px; background-color: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; font-family: system-ui, -apple-system, sans-serif;">View Leads List</a>
                    </div>
                    <p style="font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 10px; margin-top: 15px; font-family: system-ui, -apple-system, sans-serif;">
                        This notification was generated automatically by NexusAI Platform Core.
                    </p>
                </div>
                """
                notifier.send_notification(subject, html_body)
            except Exception as e:
                print(f"[Notifier] Lead discovery notification send failed: {e}")
        
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
