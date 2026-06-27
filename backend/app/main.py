from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.api.workflows import router as workflows_router
from app.api.approvals import router as approvals_router
from app.api.websocket import router as ws_router
from app.api.config_api import router as config_router
from app.api.chaos_api import router as chaos_router
from app.api.webhooks import router as webhooks_router
from app.api.agents import router as agents_router
from app.protocols.mcp_server import router as mcp_router
from app.protocols.a2a_cards import router as a2a_router
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan handler (replaces deprecated @app.on_event)."""
    print("NexusAI platform core initializing...")
    try:
        start_scheduler()
    except Exception as e:
        print(f"Failed to start scheduler: {e}")
    
    try:
        yield  # App is running
    except asyncio.CancelledError:
        pass
    finally:
        print("NexusAI platform shutting down...")
        try:
            shutdown_scheduler()
        except Exception as e:
            print(f"Failed to stop scheduler: {e}")


app = FastAPI(
    title="NexusAI API",
    description="Agentic AI Platform for B2B Customer Discovery & Prospect Intelligence",
    version="3.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Core API Routers
app.include_router(workflows_router)
app.include_router(approvals_router)
app.include_router(ws_router)
app.include_router(config_router)
app.include_router(chaos_router)
app.include_router(webhooks_router)
app.include_router(agents_router)

# Mount Protocol Routers (MCP + A2A)
app.include_router(mcp_router)
app.include_router(a2a_router)


@app.get("/")
async def root():
    return {
        "platform": "NexusAI",
        "version": "3.0.0",
        "status": "online",
        "protocols": {
            "mcp": "/v2/mcp/manifest",
            "a2a": "/v2/a2a/.well-known/agent.json",
        },
        "docs": "/docs",
    }


@app.get("/v2/observability/traces")
async def get_traces():
    """Get all observability traces."""
    from app.observability.tracer import workflow_tracer
    return workflow_tracer.get_all_traces()


@app.get("/v2/observability/traces/{trace_id}")
async def get_trace_detail(trace_id: str):
    """Get waterfall view of a specific trace."""
    from app.observability.tracer import workflow_tracer
    return {"trace_id": trace_id, "spans": workflow_tracer.get_waterfall(trace_id)}


@app.get("/v2/observability/metrics")
async def get_metrics():
    """Get LLM usage metrics."""
    from app.observability.metrics import metrics_collector
    return metrics_collector.get_summary()


@app.get("/v2/observability/metrics/recent")
async def get_recent_metrics():
    """Get recent LLM call metrics."""
    from app.observability.metrics import metrics_collector
    return {"calls": metrics_collector.get_recent_calls()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
