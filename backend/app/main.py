from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.workflows import router as workflows_router
from app.api.approvals import router as approvals_router
from app.api.websocket import router as ws_router
from app.api.config_api import router as config_router
from app.api.chaos_api import router as chaos_router
from app.api.webhooks import router as webhooks_router
from app.api.agents import router as agents_router
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.config import settings

app = FastAPI(
    title="NexusAI API",
    description="Agentic AI Platform for B2B Customer Discovery & Prospect Intelligence",
    version="3.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(workflows_router)
app.include_router(approvals_router)
app.include_router(ws_router)
app.include_router(config_router)
app.include_router(chaos_router)
app.include_router(webhooks_router)
app.include_router(agents_router)

@app.on_event("startup")
async def startup_event():
    print("NexusAI platform core initializing...")
    # Start the background task worker APScheduler
    try:
        start_scheduler()
    except Exception as e:
        print(f"Failed to start scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    print("NexusAI platform shutting down...")
    try:
        shutdown_scheduler()
    except Exception as e:
        print(f"Failed to stop scheduler: {e}")

@app.get("/")
async def root():
    return {
        "platform": "NexusAI",
        "version": "3.0.0",
        "status": "online"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
