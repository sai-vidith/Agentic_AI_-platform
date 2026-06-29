import asyncio
from app.core.planner import planner_agent
from app.core.dag_executor import DAGExecutor

async def main():
    try:
        dag = await planner_agent.create_plan("hr_saas", "RazorX Fintech")
        executor = DAGExecutor(dag)
        await executor.execute()
        print("FINISHED SUCCESSFULLY. Waiting for background tasks/Kimi audit to complete...")
        await asyncio.sleep(6.0)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
