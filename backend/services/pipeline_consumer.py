"""
Redis Streams consumer / pipeline processor.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Callable, Any

import redis.asyncio as aioredis
from bson import ObjectId
import numpy as np

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

# ── Noise Filter ──────────────────────────────────────────────────────────────
# Drops MongoDB internal healthcheck logs BEFORE they touch ML or the DB.
# These are Docker healthcheck pings via mongosh — completely harmless but
# the ML scores them 1.000 disaster because of their unusual structure.

_MONGO_MSG_NOISE = re.compile(
    r"(Connection accepted|Connection ended|client metadata"
    r"|Connection not authenticating"
    r"|Received first command on ingress connection"
    r"|mongosh\s+\d+\.\d+\.\d+)",
    re.I,
)

_MONGO_NOISE_SOURCES = frozenset({"NETWORK", "ACCESS", "CONTROL", "STORAGE", "REPL"})
_HEALTHCHECK_APPS   = frozenset({"mongosh 2.8.2", "mongosh"})


def _is_noise(log: dict) -> bool:
    """
    Returns True for logs that must be silently dropped before ML scoring.
    Covers MongoDB internal housekeeping produced by Docker healthchecks.
    """
    source   = str(log.get("source",  "")).upper()
    message  = str(log.get("message", ""))
    raw      = str(log.get("raw",     ""))
    combined = message + " " + raw

    # MongoDB internal component names (c-field in structured logs)
    if any(noise in source for noise in _MONGO_NOISE_SOURCES):
        return True

    # Known housekeeping message strings
    if _MONGO_MSG_NOISE.search(combined):
        return True

    # Raw MongoDB structured log leaked as a stringified Python dict
    # e.g. "{'t': {'$date': ...}, 's': 'I', 'c': 'NETWORK', ...}"
    if "'$date'" in combined and (
        "'c': 'NETWORK'" in combined or '"c":"NETWORK"' in combined
    ):
        return True

    # Docker healthcheck application name inside attr.doc
    app_name = (
        log.get("attr", {})
           .get("doc", {})
           .get("application", {})
           .get("name", "")
    )
    if app_name in _HEALTHCHECK_APPS:
        return True

    return False


# ── Consumer ──────────────────────────────────────────────────────────────────

class PipelineConsumer:
    def __init__(self, broadcast_fn: Callable):
        self._broadcast    = broadcast_fn
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

        # ── NOISE GATE ────────────────────────────────────────────────────────
        # Drop MongoDB internal healthcheck logs before ANY processing.
        # Without this, mongosh pings every 10 s score 1.000 disaster because
        # the ML has never seen their unusual nested structure before.
        if _is_noise(log):
            logger.debug("Noise filtered (entry %s): %s", entry_id, log.get("message", ""))
            return
        # ─────────────────────────────────────────────────────────────────────

        fe = await self._get_feature_eng()
        ml = get_ml_engine()

        features = fe.extract(log)
        ml.add_to_buffer(features)
        ml.maybe_retrain()
        
        # New: Pass message for supervised classification
        ml_result = ml.predict(features, message=str(log.get("message", "")))

        # Handle backward compatibility: tuple (old engine) vs MLResult
        if isinstance(ml_result, tuple):
            score, is_anomaly = ml_result
            ml_detail = {}
        else:
            score       = ml_result.score
            is_anomaly  = ml_result.is_anomaly
            ml_detail   = {
                "if_score":       ml_result.if_score,
                "lof_score":      ml_result.lof_score,
                "svm_score":      ml_result.svm_score,
                "supervised_sev": ml_result.supervised_sev,
                "supervised_conf":ml_result.supervised_conf,
                "confidence":     ml_result.confidence,
                "drift_detected": ml_result.drift_detected,
            }

        # New: Pass full ml_result to classify and get final anomaly decision
        severity_result, final_is_anomaly = classify(log, ml_result)

        log["severity"]        = severity_result.severity
        log["anomaly_score"]   = score
        log["is_anomaly"]      = final_is_anomaly

        log["severity_reason"] = severity_result.reason
        log["human_insight"]   = severity_result.insight
        log["ml_detail"]       = ml_detail

        # GeoIP enrichment
        ip = log.get("ip", "")
        if ip and settings.ENABLE_GEOIP:
            log["geo"] = geoip_lookup(ip)

        # Sanitize NumPy types before MongoDB insertion
        log = self._sanitize_for_db(log)

        # Store in MongoDB
        db = get_db()
        result = await db["logs"].insert_one(log)
        log["_id"] = str(result.inserted_id)

        # Store alert in PostgreSQL if High / Disaster
        if severity_result.severity in ("high", "disaster"):
            async with AsyncSessionLocal() as session:
                alert = Alert(
                    log_id        = str(result.inserted_id),
                    severity      = severity_result.severity,
                    source        = log.get("source", "unknown"),
                    message       = str(log.get("message", ""))[:1000],
                    ip            = ip or "",
                    anomaly_score = float(score),
                )
                session.add(alert)
                await session.commit()
            await alert_service.send_alert(log, severity_result.severity, severity_result.reason)

        # Broadcast to WebSocket subscribers
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
                if "NOGROUP" in str(exc):
                    logger.warning("Redis group/stream missing. Attempting to recreate...")
                    await self._ensure_group(r)
                else:
                    logger.error("Consumer loop error: %s", exc)
                await asyncio.sleep(3)

