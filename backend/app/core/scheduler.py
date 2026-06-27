from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.planner import planner_agent
from app.core.dag_executor import DAGExecutor
from app.config import settings
import asyncio

scheduler = AsyncIOScheduler()

async def run_discovery_workflow(domain: str, company_name: str):
    """Interval execution target matching manual trigger flow."""
    print(f"Background cron triggered for {domain} and target {company_name}")
    try:
        dag = await planner_agent.create_plan(domain, company_name)
        executor = DAGExecutor(dag)
        await executor.execute()
    except Exception as e:
        print(f"Background discovery failed: {e}")

def start_scheduler():
    # Schedule a background scan every 5 minutes for demonstration (golden path AcmeCorp)
    scheduler.add_job(
        run_discovery_workflow,
        trigger="interval",
        minutes=5,
        args=["hr_saas", "AcmeCorp"],
        id="discovery_acmecorp",
        replace_existing=True
    )
    scheduler.start()
    print("APScheduler engine started background loop.")

def shutdown_scheduler():
    scheduler.shutdown()
    print("APScheduler engine stopped.")
