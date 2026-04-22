"""
Stats / aggregation routes powering dashboard charts.
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from database.mongo import get_db
from database.postgres import get_db_session
from middleware.auth_middleware import get_current_user
from models.db_models import User, Alert
from models.schemas import SummaryStats
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=SummaryStats)
async def summary(
    current_user: User = Depends(get_current_user),
    db_pg: AsyncSession = Depends(get_db_session),
):
    db = get_db()
    total_logs = await db["logs"].count_documents({})
    total_anomalies = await db["logs"].count_documents({"is_anomaly": True})

    # Severity distribution
    severity_pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
    ]
    severity_counts = {doc["_id"]: doc["count"] async for doc in db["logs"].aggregate(severity_pipeline)}

    # Source distribution
    source_pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]
    source_counts = {doc["_id"]: doc["count"] async for doc in db["logs"].aggregate(source_pipeline)}

    # Alerts count
    alert_count_result = await db_pg.execute(select(func.count()).select_from(Alert))
    total_alerts = alert_count_result.scalar() or 0

    # Logs per minute (last 5 min)
    five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    recent = await db["logs"].count_documents({"timestamp": {"$gte": five_min_ago}})
    lpm = round(recent / 5, 2)

    return SummaryStats(
        total_logs=total_logs,
        total_anomalies=total_anomalies,
        total_alerts=total_alerts,
        severity_counts=severity_counts,
        source_counts=source_counts,
        logs_per_minute=lpm,
    )


@router.get("/trend")
async def trend(
    hours: int = Query(6, ge=1, le=72),
    current_user: User = Depends(get_current_user),
):
    """Returns per-hour log counts for the last N hours."""
    db = get_db()
    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "$substr": ["$timestamp", 0, 13]   # group by YYYY-MM-DDTHH
                },
                "count": {"$sum": 1},
                "anomalies": {"$sum": {"$cond": [{"$eq": ["$is_anomaly", True]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]


@router.get("/top-ips")
async def top_ips(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    db = get_db()
    pipeline = [
        {"$match": {"ip": {"$ne": "", "$exists": True}}},
        {"$group": {"_id": "$ip", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    return [{"ip": doc["_id"], "count": doc["count"]} async for doc in db["logs"].aggregate(pipeline)]


@router.get("/severity-trend")
async def severity_trend(
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user),
):
    """Per-hour severity breakdown."""
    db = get_db()
    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "hour": {"$substr": ["$timestamp", 0, 13]},
                    "severity": "$severity",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.hour": 1}},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]
