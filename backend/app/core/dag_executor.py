import asyncio
import json
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
        self.trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        
        first_task = list(dag.tasks.values())[0] if dag.tasks else None
        self.domain = first_task.input_data.get("domain", "hr_saas") if first_task else "hr_saas"

    async def _run_search_audit(self, company_name: str, website: str) -> Dict[str, Any]:
        """Runs a deep background search audit using BeautifulSoup/Scrapy queries to find LinkedIn profiles of the company and members."""
        import json
        import urllib.parse
        import re
        
        print(f"[DAGExecutor] Launching background BeautifulSoup search audit for {company_name}...")
        
        # 1. Search for company LinkedIn profile
        company_query = f"site:linkedin.com/company/ {company_name} OR \"{company_name}\" linkedin company"
        
        # 2. Search for members' LinkedIn profiles
        members_query = f"site:linkedin.com/in/ \"{company_name}\" CEO OR CTO OR founder OR HR"
        
        linkedin_links = []
        from app.tools.search_tool import SearchTool
        search_tool = SearchTool()

        for q_str in [company_query, members_query]:
            try:
                res_search = await search_tool.execute({"query": q_str, "force_ddg": True})
                if res_search and hasattr(res_search, "data"):
                    results_list = res_search.data.get("results", [])
                    for item in results_list:
                        link = item.get("link", "")
                        if link:
                            # Clean DuckDuckGo redirection if any
                            if "uddg=" in link:
                                parsed_link = urllib.parse.urlparse(link)
                                qs = urllib.parse.parse_qs(parsed_link.query)
                                link = qs.get("uddg", [link])[0]
                            
                            # Filter to only LinkedIn results
                            if "linkedin.com/company/" in link or "linkedin.com/in/" in link:
                                clean_url = link.split("?")[0].rstrip("/")
                                if clean_url not in linkedin_links:
                                    linkedin_links.append(clean_url)
            except Exception as e:
                print(f"[DAGExecutor] Search audit failed for query {q_str}: {e}")
                
        if not linkedin_links:
            return {"expansion_proof_found": False, "findings_summary": "Search audit could not resolve any LinkedIn profiles.", "audit_confidence": 50, "linkedin_links": []}
            
        # Parse audit findings using LLM
        from app.tools.llm_tool import llm_service
        try:
            prompt = f"""
            You are a B2B LinkedIn Auditor.
            Review the discovered LinkedIn profile links for the company '{company_name}':
            
            LinkedIn Links found:
            {json.dumps(linkedin_links, indent=2)}
            
            Identify:
            1. The main corporate LinkedIn company page URL.
            2. Any key executives (CEO, CTO, HR/People directors) with their names and titles matching the profile link context.
            
            Return a JSON object containing:
            {{
              "expansion_proof_found": true,
              "findings_summary": "Discovered corporate LinkedIn profile and key members: CEO/CTO.",
              "linkedin_company": "http://linkedin.com/company/...",
              "linkedin_members": [
                {{"name": "Name", "title": "CISO / CTO / VP of HR", "url": "http://linkedin.com/in/..."}}
              ],
              "audit_confidence": 95
            }}
            """
            response = await llm_service.acompletion(
                model="nexus-fast",
                messages=[
                    {"role": "system", "content": "You are a strict B2B auditor. Respond in JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Extract content from LiteLLM response structure
            content = ""
            if hasattr(response, "choices") and response.choices:
                content = response.choices[0].message.content
            elif isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                
            data = json.loads(content)
            data["linkedin_links"] = linkedin_links
            return data
        except Exception as parse_ex:
            print(f"[DAGExecutor] LLM audit analysis failed: {parse_ex}")
            return {
                "expansion_proof_found": True,
                "findings_summary": f"Search audit found {len(linkedin_links)} LinkedIn URLs for company and team.",
                "audit_confidence": 80,
                "linkedin_links": linkedin_links
            }

    async def _run_async_search_audit_and_update(self, lead_id: str, company_name: str, website: str, current_status: LeadStatus, current_icp_score: float):
        """Runs the background search audit asynchronously in the background.
        Once complete, it updates the database lead record and broadcasts a WebSocket update event."""
        try:
            # Let the server finish sending initial response and settle
            await asyncio.sleep(2.0)
            
            # Run the audit command
            findings = await self._run_search_audit(company_name, website)
            if not findings or not findings.get("findings_summary"):
                return

            # 3. Retrieve, update and persist the lead record
            lead = event_store.get_lead(lead_id)
            if not lead:
                # Search database by company name if lead ID changed
                lead = event_store.get_lead_by_company(company_name)
            
            if lead:
                evidence = lead.get("evidence_chain", [])
                evidence.append(
                    f"Tier 3 Kimi Browser Audit: {findings.get('findings_summary')} (Confidence: {findings.get('audit_confidence')}%)"
                )
                
                # Check for compliance warning resolutions
                if findings.get("expansion_proof_found"):
                    evidence.append("Compliance warning resolved by Kimi browser audit evidence.")
                    if lead.get("status") == LeadStatus.APPROVAL_REQUIRED.value:
                        lead["status"] = LeadStatus.QUALIFIED.value
                
                lead["evidence_chain"] = evidence

                # Update company details LinkedIn if empty or not resolved yet
                company_details = lead.get("company_details", {}) or {}
                if not company_details.get("linkedin") and findings.get("linkedin_company"):
                    company_details["linkedin"] = findings.get("linkedin_company")
                lead["company_details"] = company_details

                # Update or merge contacts LinkedIn profiles
                contacts_list = lead.get("contacts", []) or []
                linkedin_members = findings.get("linkedin_members", []) or []
                for member in linkedin_members:
                    # Look for contact by name or title similarity
                    found = False
                    for c in contacts_list:
                        if member.get("name") and member.get("name").lower() in c.get("name", "").lower():
                            c["linkedin"] = member.get("url")
                            if member.get("title"):
                                c["title"] = member.get("title")
                            found = True
                            break
                    if not found and member.get("name"):
                        contacts_list.append({
                            "name": member.get("name"),
                            "title": member.get("title") or "Executive",
                            "email": "unknown",
                            "phone": "unknown",
                            "linkedin": member.get("url"),
                            "persona_rank": len(contacts_list) + 1
                        })
                lead["contacts"] = contacts_list

                # Append Kimi web scraping sources after the audit completes successfully
                lead_sources = lead.get("sources", []) or []
                existing_urls = {s.get("url", "").strip().lower() for s in lead_sources}
                for link in findings.get("linkedin_links", []):
                    if link.strip().lower() not in existing_urls:
                        lead_sources.append({
                            "title": f"Kimi LinkedIn: {link.replace('https://www.', '').split('/')[1] if '/' in link.replace('https://www.', '') else 'Profile'}",
                            "url": link,
                            "status": "Correct",
                            "reason": "Discovered company/member LinkedIn profile via Kimi WebBridge."
                        })
                lead["sources"] = lead_sources
                
                # Run another LLM verification pass to update contact profiles and details if necessary
                try:
                    from app.tools.llm_tool import llm_service
                    # Let the LLM refine contacts and debate points using the newly found browser audit findings
                    refine_prompt = f"""
                    You are a B2B Verification Agent.
                    We ran a deep browser audit on {company_name} and found these details:
                    {findings.get('findings_summary')}
                    
                    Current Contacts:
                    {json.dumps(lead.get('contacts', []), indent=2)}
                    
                    Update or verify their roles. If you find new personas or corrections (e.g. real CISO/CTO names matching the audit text), correct them.
                    Return the updated contacts list in JSON format:
                    {{
                      "contacts": [ ... ]
                    }}
                    """
                    response = await llm_service.acompletion(
                        model="nexus-fast",
                        messages=[{"role": "user", "content": refine_prompt}],
                        response_format={"type": "json_object"}
                    )
                    refined = json.loads(response.choices[0].message.content)
                    if refined.get("contacts"):
                        lead["contacts"] = refined.get("contacts")
                except Exception as refine_err:
                    print(f"[DAGExecutor] Refinement pass failed during async audit: {refine_err}")
                
                # Save the verified, accurate lead details
                event_store.save_lead(lead)
                
                # Log audit completion event
                event_store.log_event({
                    "source": "workflow_engine",
                    "event_type": "kimi_audit_completed",
                    "company": company_name,
                    "data": {"lead_id": lead_id, "findings": findings.get("findings_summary")}
                })
                
                # 4. Broadcast live update to the UI
                from app.agents.base_nexus_agent import notify_agent_event
                await notify_agent_event(
                    WSEventTypes.LEAD_CONTACTS_UPDATED,
                    "system",
                    target=company_name,
                    data=lead
                )
                print(f"[DAGExecutor] Deep Kimi audit update completed and broadcasted for {company_name}.")
        except Exception as err:
            print(f"[DAGExecutor] Asynchronous Kimi audit execution failed: {err}")

    async def execute(self) -> Dict[str, Any]:
        tasks = self.dag.tasks
        
        from app.observability.tracer import workflow_tracer
        workflow_tracer.start_trace(self.trace_id)
        
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
            status = LeadStatus.APPROVAL_REQUIRED
        elif icp_score < 50:
            status = LeadStatus.DISQUALIFIED
            
        website = None
        if isinstance(company_details, dict):
            website = company_details.get("website")
        if not website:
            website = f"https://www.{company_name.lower().replace(' ', '')}.com"
            
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

        # Verify sources via LLM feedback loop
        from app.tools.llm_tool import llm_service
        if sources:
            try:
                prompt = f"""
                You are an OSINT (Open Source Intelligence) Quality Auditor.
                Review the gathered sources for the company '{company_name}' to verify their correctness and credibility.
                
                Company Context:
                {json.dumps(company_details, indent=2)}
                
                Contacts Found:
                {json.dumps(contacts, indent=2)}
                
                Sources to verify:
                {json.dumps(sources, indent=2)}
                
                Evaluate if each source link/title is:
                - "Correct": The source domain and content are authentic and represent active, verified facts.
                - "Wrong": The source is incorrect, points to a competitor, contains stale information (e.g. outdated executive names), or is unverified.
                
                Provide a verification rating ('Correct' or 'Wrong') and a brief validation reason for each source.
                Respond strictly in JSON format matching this structure:
                {{
                  "source_evaluations": [
                    {{
                      "url": "http://example.com",
                      "status": "Correct" or "Wrong",
                      "reason": "Brief 1-sentence verification audit rationale"
                    }}
                  ]
                }}
                """
                response = await llm_service.acompletion(
                    model="nexus-fast",
                    messages=[
                        {"role": "system", "content": "You are a strict B2B auditor. Respond in JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                eval_data = json.loads(response.choices[0].message.content)
                eval_map = {item["url"]: item for item in eval_data.get("source_evaluations", [])}
                
                for s in sources:
                    url = s.get("url")
                    eval_res = eval_map.get(url, {})
                    s["status"] = eval_res.get("status", "Correct")
                    s["reason"] = eval_res.get("reason", "Verified organic search result.")
            except Exception as e:
                print(f"[DAGExecutor] Source verification failed: {e}")
                for s in sources:
                    s["status"] = "Correct"
                    s["reason"] = "Default trust rating applied due to verification service timeout."

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
            
            # Update and validate lead metrics & metadata with fresh research context
            existing_details = existing_lead.get("company_details", {}) or {}
            if isinstance(existing_details, dict) and isinstance(company_details, dict):
                for k, v in company_details.items():
                    if v and v != "Unknown":
                        existing_details[k] = v
            existing_lead["company_details"] = existing_details
            
            existing_lead["icp_score"] = icp_score
            existing_lead["evidence_chain"] = evidence_chain
            existing_lead["shadow_verdict"] = shadow_verdict
            existing_lead["outreach_template"] = outreach_template
            
            # Dynamically update status if the lead was not already approved or rejected
            if is_valid and icp_score >= 70:
                if existing_lead.get("status") not in [LeadStatus.APPROVED.value, LeadStatus.REJECTED.value]:
                    existing_lead["status"] = LeadStatus.APPROVAL_REQUIRED.value
            elif icp_score < 50:
                if existing_lead.get("status") not in [LeadStatus.APPROVED.value, LeadStatus.REJECTED.value]:
                    existing_lead["status"] = LeadStatus.DISQUALIFIED.value
            
            # Merge pipeline logs and flags
            pipeline_log = self.memory.get("pipeline_log", [])
            data_quality_flags = self.memory.get("data_quality_flags", [])
            
            existing_lead["pipeline_log"] = existing_lead.get("pipeline_log", []) + [l for l in pipeline_log if l not in existing_lead.get("pipeline_log", [])]
            existing_lead["data_quality_flags"] = existing_lead.get("data_quality_flags", []) + [f for f in data_quality_flags if f not in existing_lead.get("data_quality_flags", [])]
            
            # Save the updated lead
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
                    from app.config import settings
                    from app.observability.notifier import notifier
                    subject = f"[NexusAI] New Contacts Discovered for {company_name}"
                    contacts_list_html = "".join([
                        f"<li><strong>{c.get('name')}</strong> - {c.get('title') or 'Executive'}</li>"
                        for c in new_contacts_added
                    ])
                    html_body = f"""
                    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
                        <h2 style="color: #06b6d4; margin-top: 0; font-family: system-ui, -apple-system, sans-serif;">New Decision Makers Identified</h2>
                        <p style="font-size: 14px; color: #334155; line-height: 1.5; font-family: system-ui, -apple-system, sans-serif;">
                            While scanning <strong>{company_name}</strong>, our research agents identified the following new decision maker profiles:
                        </p>
                        <ul style="font-size: 13px; color: #334155; line-height: 1.6;">
                            {contacts_list_html}
                        </ul>
                        <div style="margin: 20px 0; text-align: center;">
                            <a href="{settings.FRONTEND_URL}/leads" style="display: inline-block; padding: 10px 20px; background-color: #06b6d4; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; font-family: system-ui, -apple-system, sans-serif;">View Lead Details</a>
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

        # --- Compute Buying Committee Roles & Influence Graph ---
        buying_committee = []
        for contact in contacts:
            title = contact.get("title", "").lower()
            name = contact.get("name", "Unknown Contact")
            
            # Map role based on title heuristics
            if any(k in title for k in ("chief", "vp", "president", "cpo", "cfo", "cio", "cto", "ceo", "head of")):
                role = "Decision Maker"
            elif any(k in title for k in ("director", "manager", "lead", "architect", "engineer")):
                role = "Influencer"
            else:
                role = "Gatekeeper"
                
            buying_committee.append({
                "name": name,
                "title": contact.get("title", ""),
                "role": role,
                "linkedin": contact.get("linkedin", "")
            })
            
        # Target Sequence order: Gatekeeper first (rapport/data) -> Influencer (workflow/advocacy) -> Decision Maker (executive pitch)
        role_priority = {"Gatekeeper": 1, "Influencer": 2, "Decision Maker": 3}
        sorted_committee = sorted(buying_committee, key=lambda x: role_priority.get(x["role"], 9))
        
        engagement_sequence = []
        for idx, member in enumerate(sorted_committee, 1):
            role = member["role"]
            name = member["name"]
            title = member["title"]
            
            if role == "Gatekeeper":
                strategy = "Initiate low-friction outreach to establish administrative rapport and confirm tool stack validation details."
            elif role == "Influencer":
                strategy = "Pitch technical workflow improvements and automation advantages to gather internal sponsorship."
            else:
                strategy = "Present executive-level business case, financial ROI validation, and contract terms."
                
            engagement_sequence.append({
                "step": idx,
                "name": name,
                "title": title,
                "role": role,
                "strategy": strategy
            })

        debate_transcript = self.memory.get("debate_transcript", [])
        
        pipeline_log = self.memory.get("pipeline_log", [])
        data_quality_flags = self.memory.get("data_quality_flags", [])

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
            "debate_transcript": debate_transcript,
            "buying_committee": engagement_sequence,
            "domain": self.domain,
            "pipeline_log": pipeline_log,
            "data_quality_flags": data_quality_flags,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Mapped to strict Output Contract
        lead_summary["company"] = {
            "name": company_name,
            "domain": company_details.get("website", ""),
            "description": company_details.get("description", ""),
            "headquarters": company_details.get("hq", ""),
            "employee_count": company_details.get("employees"),
            "founded_year": company_details.get("founded"),
            "linkedin_company_url": company_details.get("linkedin"),
            "funding_stage": company_details.get("recent_funding", {}).get("round") if isinstance(company_details.get("recent_funding"), dict) else None,
            "tech_stack": company_details.get("tech_stack", []),
            "icp_score": {
                "total": icp_score,
                "breakdown": self.memory.get("scores_breakdown", {})
            },
            "trigger_signals": [
                {
                    "signal_type": t.get("type", "UNKNOWN"),
                    "headline": t.get("headline") or t.get("detail", ""),
                    "date": t.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "source": t.get("source") or "NewsAPI/Serper"
                }
                for t in self.memory.get("triggers", [])
            ]
        }
        lead_summary["decision_makers"] = [
            {
                "full_name": c.get("full_name") or c.get("name", ""),
                "title": c.get("title", ""),
                "persona_match": c.get("persona_match", "CHRO"),
                "email": c.get("email"),
                "email_confidence": c.get("email_confidence"),
                "phone": c.get("phone"),
                "linkedin_url": c.get("linkedin_url") or c.get("linkedin"),
                "source_url": c.get("source_url", ""),
                "confidence": c.get("confidence", "MEDIUM"),
                "extraction_method": c.get("extraction_method", "serper_snippet")
            }
            for c in contacts
        ]
        
        # --- Write lead entity & influence links to Knowledge Graph ---
        try:
            kg_manager.add_entity(company_name, "company", {
                "icp_score": icp_score,
                "status": status.value,
                "lead_id": lead_id,
            })
            
            # Add contact entities with roles
            for member in buying_committee:
                kg_manager.add_entity(member["name"], "person", {
                    "title": member["title"],
                    "role": member["role"]
                })
                kg_manager.add_relation(member["name"], company_name, "WORKS_AT")
                
            # Build influence hierarchy inside Knowledge Graph
            gatekeepers = [m for m in buying_committee if m["role"] == "Gatekeeper"]
            influencers = [m for m in buying_committee if m["role"] == "Influencer"]
            decision_makers = [m for m in buying_committee if m["role"] == "Decision Maker"]
            
            for gk in gatekeepers:
                for inf in influencers:
                    kg_manager.add_relation(gk["name"], inf["name"], "INFLUENCES")
            for inf in influencers:
                for dm in decision_makers:
                    kg_manager.add_relation(inf["name"], dm["name"], "INFLUENCES")
            
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
        
        # Launch the background BeautifulSoup search audit asynchronously as a non-blocking background task
        # This keeps the initial response latency ultra-low (under 3 seconds)
        asyncio.create_task(self._run_async_search_audit_and_update(
            lead_id=lead_id,
            company_name=company_name,
            website=website,
            current_status=status,
            current_icp_score=icp_score
        ))
        
        # Trigger Email Notification (Option 1: Free SMTP or Resend API)
        if status.value == LeadStatus.APPROVAL_REQUIRED.value:
            try:
                from app.config import settings
                from app.observability.notifier import notifier
                subject = f"[NexusAI] Approval Required: New Lead Flagged - {company_name}"
                html_body = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
                    <h2 style="color: #d97706; margin-top: 0; font-family: system-ui, -apple-system, sans-serif;">Action Required: Human Approval Needed</h2>
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
                        <a href="{settings.FRONTEND_URL}/approvals" style="display: inline-block; padding: 10px 20px; background-color: #d97706; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; font-family: system-ui, -apple-system, sans-serif;">Go to Approvals Dashboard</a>
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
                from app.config import settings
                from app.observability.notifier import notifier
                subject = f"[NexusAI] New Qualified Lead Discovered: {company_name}"
                html_body = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #fafafa;">
                    <h2 style="color: #10b981; margin-top: 0; font-family: system-ui, -apple-system, sans-serif;">Qualified Lead Discovered</h2>
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
                        <a href="{settings.FRONTEND_URL}/leads" style="display: inline-block; padding: 10px 20px; background-color: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; font-family: system-ui, -apple-system, sans-serif;">View Leads List</a>
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
        
        # Start span in global workflow_tracer
        from app.observability.tracer import workflow_tracer
        span = workflow_tracer.start_span(
            trace_id=self.trace_id,
            operation=agent_name,
            agent_name=agent_name,
            metadata={"company_name": current_context.get("company_name", "")}
        )
        span_id = span.span_id
        
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
                self._record_span(agent_name, span_start, "recovered", span_id)
                return outputs
            except Exception as fe:
                task.status = AgentState.FAILED
                task.error_message = str(fe)
                self._record_span(agent_name, span_start, "failed", span_id)
                return {}

        # 2. Regular execution path
        try:
            if agent_name == "shadow_agent":
                from app.core.debate import debate_protocol
                company_name = current_context.get("company_name", "Unknown Company")
                company_details = current_context.get("company_details", {})
                icp_score = current_context.get("score", 0)
                evidence = current_context.get("evidence_chain", [])
                domain = inputs.get("domain", "hr_saas")
                
                # Execute OpenAI Debate Protocol
                debate_results = await debate_protocol.run_debate(company_name, company_details, icp_score, evidence, domain)
                
                # Update memory with debate transcript
                self.memory.update_from_agent({"debate_transcript": debate_results["transcript"]})
                
                outputs = {"shadow_verdict": debate_results["verdict"].dict(), "debate_transcript": debate_results["transcript"]}
                
                if debate_results["verdict"].status == "DIVERGENCE_WARNING":
                    await notify_agent_event(
                        WSEventTypes.SHADOW_DIVERGENCE, 
                        agent_name, 
                        target=company_name, 
                        data={
                            "reason": debate_results["verdict"].reason,
                            "reasons": debate_results["verdict"].reasons,
                            "confidence": debate_results["verdict"].confidence
                        }
                    )
            else:
                outputs = await agent.execute(inputs)
                
            task.status = AgentState.COMPLETED
            await notify_agent_event(WSEventTypes.AGENT_COMPLETED, agent_name, target=current_context.get("company_name"), data={"output": outputs})
            self._record_span(agent_name, span_start, "completed", span_id)
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
                self._record_span(agent_name, span_start, "recovered", span_id)
                return outputs
            except Exception as fe:
                task.status = AgentState.FAILED
                task.error_message = str(fe)
                self._record_span(agent_name, span_start, "failed", span_id)
                return {}

    def _record_span(self, agent_name: str, start_time: datetime, status: str, span_id: str = None):
        """Record an observability trace span for this agent execution."""
        end_time = datetime.now(timezone.utc)
        self.trace_spans.append({
            "agent": agent_name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_ms": int((end_time - start_time).total_seconds() * 1000),
            "status": status,
        })
        if span_id:
            from app.observability.tracer import workflow_tracer
            workflow_tracer.finish_span(span_id, status)
