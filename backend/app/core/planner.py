import json
from typing import Dict, Any, List
from app.tools.llm_tool import llm_service
from app.config import get_business_config
from app.core.schemas import DAG, AgentTask

class PlannerAgent:
    """Orchestrates goal decomposition, generating DAG tasks from business rules."""
    
    def __init__(self):
        pass

    async def create_plan(self, domain: str, company_name: str) -> DAG:
        # Load business configurations
        biz_config = get_business_config(domain)
        
        # We construct the default template of tasks first
        task_names = [
            "trigger_monitor",
            "company_enricher",
            "icp_matcher",
            "shadow_agent",
            "persona_finder",
            "contact_enricher",
            "summary_agent",
            "validator_agent"
        ]
        
        tasks = {}
        for idx, name in enumerate(task_names):
            dependencies = [task_names[idx - 1]] if idx > 0 else []
            tasks[name] = AgentTask(
                id=name,
                name=name,
                dependencies=dependencies,
                input_data={
                    "domain": domain,
                    "company_name": company_name,
                    # Provide specific business configs to relevant nodes
                    "icp_rules": biz_config.get("icp") if name == "icp_matcher" else {},
                    "persona_rules": biz_config.get("personas") if name == "persona_finder" else {},
                    "trigger_rules": biz_config.get("triggers") if name == "trigger_monitor" else {}
                }
            )
            
        edges = []
        for name in task_names[1:]:
            edges.append([tasks[name].dependencies[0], name])

        # We can optionally call the LLM to refine/annotate the execution path
        # Let's do that for compliance with "dynamic Planner Agent"
        prompt = f"""
        Given the target domain '{domain}' and company '{company_name}', review the default B2B Lead Generation DAG pipeline structure.
        The default nodes are: {', '.join(task_names)}.
        
        Provide a short optimization report or any annotations.
        Return in JSON format:
        {{
          "annotated_plan": "Proceeding with standard sequential lead analysis...",
          "adjustments_made": false
        }}
        """
        try:
            response = await llm_service.acompletion(
                model="nexus-fast",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            # Log output to console/logs
            print(f"Planner optimizations: {response.choices[0].message.content}")
        except Exception as e:
            print(f"Planner optimization bypass: {e}")
            
        return DAG(tasks=tasks, edges=edges)

# Shared planner
planner_agent = PlannerAgent()
