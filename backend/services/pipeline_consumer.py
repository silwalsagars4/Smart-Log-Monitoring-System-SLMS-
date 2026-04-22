"""
Redis Streams consumer / pipeline processor.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Any

import redis.asyncio as aioredis
from bson import ObjectId
import numpy as np  # Added for type checking

from config import get_settings
from database.mongo import get_db
from database.postgres import AsyncSessionLocal
from models.db_models import Alert
from services.feature_engineer import FeatureEngineer
from services.ml_engine import get_ml_engine
from services.severity_classifier import classify
from services.geoip_service import lookup as geoip_lookup
from services import alert_service

logger = logging.getLogger(__name__)
settings = get_settings()

STREAM_KEY = "slms:logs"
GROUP_NAME = "slms-processors"
CONSUMER_NAME = "backend-1"


class PipelineConsumer:
    def __init__(self, broadcast_fn: Callable):
        self._broadcast = broadcast_fn  # injected by main app
        self._redis: aioredis.Redis | None = None
        self._feature_eng: FeatureEngineer | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def _ensure_group(self, r: aioredis.Redis):
        try:
            await r.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
            logger.info("Created consumer group '%s'", GROUP_NAME)
        except Exception:
            pass  # already exists

    async def _get_feature_eng(self) -> FeatureEngineer:
        if self._feature_eng is None:
            import redis as redis_sync
            r_sync = redis_sync.from_url(settings.REDIS_URL, decode_responses=True)
            self._feature_eng = FeatureEngineer(r_sync)
        return self._feature_eng

    def _sanitize_for_db(self, data: Any) -> Any:
        """
        Recursively converts NumPy types to standard Python types to ensure
        BSON/JSON serialisation works for MongoDB and WebSockets.
        """
        if isinstance(data, dict):
            return {k: self._sanitize_for_db(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_db(v) for v in data]
        elif isinstance(data, np.bool_):
            return bool(data)
        elif isinstance(data, (np.int64, np.int32, np.int16)):
            return int(data)
        elif isinstance(data, (np.float64, np.float32)):
            return float(data)
        return data

    def _parse_entry(self, fields: dict) -> dict:
        log = {}
        for k, v in fields.items():
            try:
                parsed = json.loads(v)
                log[k] = parsed
            except (json.JSONDecodeError, TypeError):
                log[k] = v
        
        if "status" in log:
            try:
                log["status"] = int(log["status"])
            except (ValueError, TypeError):
                log["status"] = None
        return log

    async def _process(self, entry_id: str, fields: dict):
        log = self._parse_entry(fields)
        fe = await self._get_feature_eng()
        ml = get_ml_engine()

        features = fe.extract(log)
        ml.add_to_buffer(features)
        ml.maybe_retrain()
        score, is_anomaly = ml.predict(features)

        severity_result = classify(log, score, is_anomaly)
        
        # Populate log with ML results
        log["severity"] = severity_result.severity
        log["anomaly_score"] = score
        log["is_anomaly"] = is_anomaly
        log["severity_reason"] = severity_result.reason

        # GeoIP enrichment
        ip = log.get("ip", "")
        if ip and settings.ENABLE_GEOIP:
            log["geo"] = geoip_lookup(ip)

        # CRITICAL: Sanitize data before MongoDB insertion to prevent NumPy encoding errors
        log = self._sanitize_for_db(log)

        # Store in MongoDB
        db = get_db()
        result = await db["logs"].insert_one(log)
        log["_id"] = str(result.inserted_id)

        # Store alert in PostgreSQL if High/Disaster
        if severity_result.severity in ("high", "disaster"):
            async with AsyncSessionLocal() as session:
                alert = Alert(
                    log_id=str(result.inserted_id),
                    severity=severity_result.severity,
                    source=log.get("source", "unknown"),
                    message=str(log.get("message", ""))[:1000],
                    ip=ip or "",
                    anomaly_score=float(score), # Ensure float
                )
                session.add(alert)
                await session.commit()
            await alert_service.send_alert(log, severity_result.severity, severity_result.reason)

        # Broadcast to WebSocket subscribers
        # (Sanitization already handled by _sanitize_for_db)
        log_out = {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in log.items()}
        await self._broadcast(log_out)

    async def run(self):
        r = await self._get_redis()
        await self._ensure_group(r)
        logger.info("Pipeline consumer started. Listening on stream '%s'…", STREAM_KEY)

        while True:
            try:
                entries = await r.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME, {STREAM_KEY: ">"}, count=50, block=1000
                )
                if not entries:
                    continue

                for _stream, messages in entries:
                    for entry_id, fields in messages:
                        try:
                            await self._process(entry_id, fields)
                            await r.xack(STREAM_KEY, GROUP_NAME, entry_id)
                        except Exception as exc:
                            logger.error("Failed to process entry %s: %s", entry_id, exc)
            except Exception as exc:
                logger.error("Consumer loop error: %s", exc)
                await asyncio.sleep(3)