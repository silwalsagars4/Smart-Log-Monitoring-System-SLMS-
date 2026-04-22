"""
Feature engineering — converts structured log dicts into numeric feature vectors
using sliding-window aggregations kept in Redis.
"""

import json
import math
import time
from typing import Optional

import redis as redis_lib

WINDOW_SECONDS = 300  # 5-min rolling window


class FeatureEngineer:
    def __init__(self, redis_client: redis_lib.Redis):
        self.redis = redis_client

    def _key(self, namespace: str, value: str) -> str:
        return f"slms:fe:{namespace}:{value}"

    def _increment(self, key: str, ttl: int = WINDOW_SECONDS):
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        pipe.execute()

    def _get(self, key: str) -> int:
        v = self.redis.get(key)
        return int(v) if v else 0

    def extract(self, log: dict) -> list[float]:
        """
        Returns a feature vector [f0..f7] for Isolation Forest:
          0 — log source one-hot index
          1 — http status code (0 if N/A)
          2 — is_error flag
          3 — per-IP request count (5-min window)
          4 — per-IP failure count (5-min window)
          5 — global events in last 5 min
          6 — hour of day (0-23) for time-pattern features
          7 — response bytes (0 if N/A)
        """
        source = log.get("source", "unknown")
        ip = log.get("ip", "unknown") or "unknown"
        event_type = log.get("event_type", "") or ""
        status = self._safe_int(log.get("status"))
        is_error = 1 if (
            status and status >= 400
            or "error" in event_type
            or "failure" in event_type
            or "crash" in event_type
        ) else 0
        is_failure = 1 if ("failure" in event_type or "brute" in event_type or "crash" in event_type) else 0

        # Update counters
        self._increment(self._key("ip_count", ip))
        if is_failure:
            self._increment(self._key("ip_fail", ip))
        self._increment(self._key("global_events", "all"))

        ip_count = self._get(self._key("ip_count", ip))
        ip_fail = self._get(self._key("ip_fail", ip))
        global_events = self._get(self._key("global_events", "all"))

        hour = time.localtime().tm_hour
        source_idx = {"ssh": 0, "nginx": 1, "apache": 2, "docker": 3, "mysql": 4}.get(source, 5)

        return [
            float(source_idx),
            float(status or 0),
            float(is_error),
            float(min(ip_count, 1000)),
            float(min(ip_fail, 100)),
            float(min(global_events, 10000)),
            float(hour),
            float(self._safe_int(log.get("bytes")) or 0),
        ]

    @staticmethod
    def _safe_int(v) -> Optional[int]:
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
