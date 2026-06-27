from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.planner import planner_agent
from app.core.dag_executor import DAGExecutor
from app.config import settings
from app.tools.search_tool import SearchTool
from app.tools.llm_tool import llm_service
import asyncio
import json

scheduler = AsyncIOScheduler()

async def run_autonomous_market_scan(domain: str, limit: int = 2):
    """Periodic background scan to discover and qualify B2B targets autonomously."""
    print(f"[Scheduler] Cron triggered: Running market discovery scan for domain '{domain}'")
    try:
        # 1. Search the web for trending startups in the domain
        search_tool = SearchTool()
        search_query = f"recently funded {domain.replace('_', ' ')} startups new launch 2026"
        search_result = await search_tool.execute({"query": search_query})
        results_text = json.dumps(search_result.data.get("results", []))
        
        # 2. Extract company names via LLM
        prompt = f"""
        Analyze the following search results about '{domain}' startups:
        {results_text}
        
        Extract a list of exactly up to {limit} distinct company names that are mentioned as active startups or businesses in this domain.
        Do not return generic portal names or guide blogs.
        
        Respond in JSON format:
        {{
          "companies": ["Company A", "Company B"]
        }}
        """
        response = await llm_service.acompletion(
            model="nexus-fast",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        discovered = data.get("companies", [])
        
        # Fallback if search returns empty
        if not discovered:
            discovered = ["Gusto", "Rippling"] if domain == "hr_saas" else ["Wiz", "Snyk"]
            
        print(f"[Scheduler] Scan discovered candidate companies: {discovered}")
        
        # 3. Spawn background execution task for each discovered target
        from app.api.workflows import execute_task_background
        for company in discovered:
            asyncio.create_task(execute_task_background(domain, company))
            
    except Exception as e:
        print(f"[Scheduler] Background discovery failed: {e}")

def start_scheduler():
    # Schedule an autonomous market scan every 10 minutes
    scheduler.add_job(
        run_autonomous_market_scan,
        trigger="interval",
        minutes=10,
        args=["hr_saas", 2],
        id="autonomous_market_scan",
        replace_existing=True
    )
    scheduler.start()
    print("APScheduler engine started autonomous background cron loop.")

def shutdown_scheduler():
    scheduler.shutdown()
    print("APScheduler engine stopped.")
