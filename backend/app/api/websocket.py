from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
from app.core.schemas import WSEvent
from app.agents.base_nexus_agent import register_agent_callback
import json
import asyncio

router = APIRouter(prefix="/v2/ws")

class ConnectionManager:
    """Manages active WebSocket connections for real-time dashboard events."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"Client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Remove stale connection
                pass

manager = ConnectionManager()

# Hook the registry callback to push agent notifications to connected clients
async def on_agent_event(event: WSEvent):
    payload = {
        "type": event.type.value,
        "agent": event.agent,
        "target": event.target,
        "data": event.data,
        "timestamp": event.timestamp.isoformat()
    }
    # Schedule broadcast in the running event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(manager.broadcast(payload))

register_agent_callback(on_agent_event)

@router.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep-alive loop
            data = await websocket.receive_text()
            # Respond to ping
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
