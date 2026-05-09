"""
Log routes — query, filter, and direct ingest.
"""

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from middleware.auth_middleware import get_current_user, require_admin, require_any_authenticated
from middleware.rate_limiter import limiter
from models.db_models import User
from models.schemas import LogsResponse, LogIngest
from database.mongo import get_db

router = APIRouter(prefix="/logs", tags=["logs"])


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"]) if "_id" in doc else None
    return doc


@router.get("", response_model=LogsResponse)
async def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    source: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
    is_anomaly: Optional[bool] = Query(None),
    current_user: User = Depends(require_any_authenticated),
):
    db = get_db()
    query: dict = {}
    if source:
        query["source"] = source
    if severity:
        query["severity"] = severity
    if is_anomaly is not None:
        query["is_anomaly"] = is_anomaly
    if search:
        query["$or"] = [
            {"message": {"$regex": search, "$options": "i"}},
            {"ip": {"$regex": search, "$options": "i"}},
            {"user": {"$regex": search, "$options": "i"}},
        ]
    if from_ts or to_ts:
        ts_filter = {}
        if from_ts:
            ts_filter["$gte"] = from_ts
        if to_ts:
            ts_filter["$lte"] = to_ts
        query["timestamp"] = ts_filter

    total = await db["logs"].count_documents(query)
    skip = (page - 1) * page_size
    cursor = db["logs"].find(query).sort("timestamp", -1).skip(skip).limit(page_size)
    docs = [_serialize(doc) async for doc in cursor]

    return LogsResponse(total=total, page=page, page_size=page_size, data=docs)


@router.post("/ingest", status_code=202)
@limiter.limit("1000/minute")
async def ingest_log(request: Request, body: LogIngest, current_user: User = Depends(require_admin)):
    """Direct log ingestion endpoint (bypasses agents — useful for custom integrations)."""
    from services.feature_engineer import FeatureEngineer
    from services.ml_engine import get_ml_engine
    from services.severity_classifier import classify
    import redis as redis_sync
    from config import get_settings

    settings = get_settings()
    r = redis_sync.from_url(settings.REDIS_URL, decode_responses=True)

    log_dict = body.model_dump(exclude_none=True)
    log_dict.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    fe = FeatureEngineer(r)
    ml = get_ml_engine()
    features = fe.extract(log_dict)
    score, is_anomaly = ml.predict(features)
    sr = classify(log_dict, score, is_anomaly)

    log_dict["severity"] = sr.severity
    log_dict["anomaly_score"] = score
    log_dict["is_anomaly"] = is_anomaly

    db = get_db()
    await db["logs"].insert_one(log_dict)
    return {"status": "accepted"}


@router.get("/{log_id}")
async def get_log(log_id: str, current_user: User = Depends(require_any_authenticated)):
    db = get_db()
    try:
        doc = await db["logs"].find_one({"_id": ObjectId(log_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid log ID")
    if not doc:
        raise HTTPException(status_code=404, detail="Log not found")
    return _serialize(doc)
