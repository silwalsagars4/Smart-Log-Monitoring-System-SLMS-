"""
System Health API — serves hardware & OS telemetry collected by the agent.

Route:  GET /api/v1/system/stats
Auth:   JWT — admin or analyst role required
Data:   Read from Redis key  slms:system_stats  (set by SystemCollector)
"""

import json
import logging

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, status

from config import get_settings
from middleware.auth_middleware import require_analyst_or_above
from models.db_models import User

logger   = logging.getLogger(__name__)
settings = get_settings()
router   = APIRouter(prefix="/v1/system", tags=["system"])

REDIS_KEY = "slms:system_stats"

# ── Redis client (lazy singleton) ─────────────────────────────────────────────
_redis_client: redis_lib.Redis | None = None


def _get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis_client


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(require_analyst_or_above),
):
    """
    Return the latest system telemetry snapshot published by the agent.
    Raises 503 if no data is available yet (agent hasn't started or Redis TTL expired).
    """
    try:
        r = _get_redis()
        # Try host stats first (from native agent)
        raw = r.get("slms:host_stats")
        if not raw:
            # Fallback to internal system stats (Docker)
            raw = r.get(REDIS_KEY)
    except Exception as exc:
        logger.warning("Redis read error for %s: %s", REDIS_KEY, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System stats temporarily unavailable — Redis error.",
        ) from exc

    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System stats not yet available — agent may still be starting.",
        )

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Corrupt system_stats JSON in Redis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System stats data is malformed.",
        ) from exc
