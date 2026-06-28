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
        from app.tools.search_tool import discover_companies_from_web
        discovered = await discover_companies_from_web(domain, limit)
            
        print(f"[Scheduler] Scan discovered candidate companies: {discovered}")
        
        # 3. Spawn background execution task for each discovered target
        from app.api.workflows import execute_task_background
        for company in discovered:
            asyncio.create_task(execute_task_background(domain, company))
            
    except Exception as e:
        print(f"[Scheduler] Background discovery failed: {e}")

def start_scheduler():
    # Schedule an autonomous market scan every 10 minutes for HR SaaS
    scheduler.add_job(
        run_autonomous_market_scan,
        trigger="interval",
        minutes=10,
        args=["hr_saas", 2],
        id="autonomous_market_scan_hr",
        replace_existing=True
    )
    # Schedule an autonomous market scan every 10 minutes for Cybersecurity
    scheduler.add_job(
        run_autonomous_market_scan,
        trigger="interval",
        minutes=10,
        args=["cybersecurity", 2],
        id="autonomous_market_scan_cyber",
        replace_existing=True
    )
    # Schedule an email digest flusher every 2 minutes
    from app.observability.notifier import notifier
    scheduler.add_job(
        notifier.send_digest,
        trigger="interval",
        minutes=2,
        id="email_digest_flusher",
        replace_existing=True
    )
    scheduler.start()
    print("APScheduler engine started autonomous background cron loop.")

def shutdown_scheduler():
    scheduler.shutdown()
    print("APScheduler engine stopped.")
