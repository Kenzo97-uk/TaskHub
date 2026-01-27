from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from redis.asyncio import Redis

load_dotenv()

API_KEY = os.getenv("API_KEY", "changeme")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
APP_NAME = os.getenv("APP_NAME", "PAR Distributed Demo")

CHANNEL_EVENTS = "par:events"

app = FastAPI(title=APP_NAME)

redis: Optional[Redis] = None
ws_clients: Set[WebSocket] = set()

# ----------------------------
# Models
# ----------------------------
class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    done: bool = False

class Task(TaskIn):
    id: str
    created_at: str

# In-memory store for simplicity (good enough for the assignment demo)
TASKS: Dict[str, Task] = {}

# ----------------------------
# Security (simple API key)
# ----------------------------
def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

# ----------------------------
# Redis helpers
# ----------------------------
async def get_redis() -> Redis:
    global redis
    if redis is None:
        redis = Redis.from_url(REDIS_URL, decode_responses=True)
    return redis

async def publish_event(event: dict):
    r = await get_redis()
    await r.publish(CHANNEL_EVENTS, json.dumps(event, ensure_ascii=False))

async def broadcast_to_websockets(message: str):
    dead = []
    for ws in list(ws_clients):
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.discard(ws)

async def redis_listener_task():
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL_EVENTS)
    try:
        async for msg in pubsub.listen():
            # msg example: {'type': 'message', 'pattern': None, 'channel': '...', 'data': '...'}
            if msg.get("type") != "message":
                continue
            data = msg.get("data")
            if isinstance(data, str):
                await broadcast_to_websockets(data)
    finally:
        await pubsub.unsubscribe(CHANNEL_EVENTS)
        await pubsub.close()

@app.on_event("startup")
async def on_startup():
    import asyncio
    # Start async Redis listener -> pushes updates to all WS clients
    app.state.redis_task = asyncio.create_task(redis_listener_task())

@app.on_event("shutdown")
async def on_shutdown():
    task = getattr(app.state, "redis_task", None)
    if task:
        task.cancel()
    global redis
    if redis:
        await redis.close()
        redis = None

# ----------------------------
# REST API (sync request/response)
# ----------------------------
@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "time": datetime.utcnow().isoformat() + "Z"}

@app.get("/tasks", dependencies=[Depends(require_api_key)], response_model=List[Task])
def list_tasks():
    return list(TASKS.values())

@app.get("/tasks/{task_id}", dependencies=[Depends(require_api_key)], response_model=Task)
def get_task(task_id: str):
    t = TASKS.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t

@app.post("/tasks", dependencies=[Depends(require_api_key)], response_model=Task, status_code=201)
async def create_task(task: TaskIn):
    task_id = str(uuid.uuid4())
    t = Task(id=task_id, title=task.title, done=task.done, created_at=datetime.utcnow().isoformat() + "Z")
    TASKS[task_id] = t

    await publish_event({
        "type": "task.created",
        "task": t.model_dump()
    })
    return t

@app.put("/tasks/{task_id}", dependencies=[Depends(require_api_key)], response_model=Task)
async def update_task(task_id: str, patch: TaskIn):
    t = TASKS.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    t = Task(id=t.id, title=patch.title, done=patch.done, created_at=t.created_at)
    TASKS[task_id] = t

    await publish_event({
        "type": "task.updated",
        "task": t.model_dump()
    })
    return t

@app.delete("/tasks/{task_id}", dependencies=[Depends(require_api_key)], status_code=204)
async def delete_task(task_id: str):
    t = TASKS.pop(task_id, None)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")

    await publish_event({
        "type": "task.deleted",
        "task": t.model_dump()
    })
    return None

# ----------------------------
# WebSocket API (async push)
# ----------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        await ws.send_text(json.dumps({"type": "hello", "app": APP_NAME}, ensure_ascii=False))
        while True:
            # We don't require client -> server messages, but we keep the connection alive.
            _ = await ws.receive_text()
            # Optional: could handle ping or commands here.
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(ws)
