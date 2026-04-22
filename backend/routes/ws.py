"""
WebSocket endpoint — streams processed log entries to connected clients.
Clients subscribe and receive real-time anomaly/log events as JSON.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])
settings = get_settings()

# ── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        logger.info("WS client connected. Total: %d", len(self._clients))

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)
        logger.info("WS client disconnected. Total: %d", len(self._clients))

    async def broadcast(self, message: Any):
        if not self._clients:
            return
        payload = json.dumps(message, default=str)
        dead = set()
        async with self._lock:
            clients = set(self._clients)
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        async with self._lock:
            self._clients -= dead


manager = ConnectionManager()


async def broadcast_log(log: dict):
    """Called by the pipeline consumer to push to all WS clients."""
    await manager.broadcast({"type": "log", "data": log})


# ── WebSocket Route ────────────────────────────────────────────────────────────

@router.websocket("/ws/logs")
async def websocket_logs(
    ws: WebSocket,
    token: str = Query(..., description="JWT token for authentication"),
):
    # Validate token before accepting
    try:
        jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(ws)
    try:
        while True:
            # Keep connection alive; client sends pings
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(ws)
