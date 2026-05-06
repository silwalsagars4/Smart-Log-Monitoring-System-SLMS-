"""
Feature engineering — converts structured log dicts into numeric feature vectors.
Upgraded to 26 features for production ML.
"""

import math
import time
from typing import Optional, Any

import redis as redis_lib

WINDOW_SECONDS = 300  # 5-min rolling window
WINDOW_1M = 60

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

    def _shannon_entropy(self, data: Any) -> float:
        if not data:
            return 0.0
        # Ensure we are working with a string
        text = str(data)
        entropy = 0
        for x in range(256):
            p_x = float(text.count(chr(x))) / len(text)
            if p_x > 0:
                entropy += - p_x * math.log(p_x, 2)
        return float(entropy)

    def extract(self, log: dict) -> list[float]:
        source = log.get("source", "unknown")
        ip = log.get("ip", "unknown") or "unknown"
        event_type = log.get("event_type", "") or ""
        status = self._safe_int(log.get("status"))
        message = str(log.get("message", ""))
        
        is_error = 1 if (status and status >= 400 or "error" in event_type or "failure" in event_type or "crash" in event_type) else 0
        is_failure = 1 if ("failure" in event_type or "brute" in event_type or "crash" in event_type) else 0

        # Extract features
        hour = time.localtime().tm_hour
        source_idx = {"ssh": 0, "nginx": 1, "apache": 2, "docker": 3, "mysql": 4, "auth": 5}.get(source, 6)
        
        # Increments
        self._increment(self._key("ip_count_5m", ip), WINDOW_SECONDS)
        self._increment(self._key("ip_count_1m", ip), WINDOW_1M)
        if is_failure:
            self._increment(self._key("ip_fail_5m", ip), WINDOW_SECONDS)
        self._increment(self._key("global_events_5m", "all"), WINDOW_SECONDS)
        self._increment(self._key("global_events_1m", "all"), WINDOW_1M)
        
        if is_error:
            self._increment(self._key("global_errors_5m", "all"), WINDOW_SECONDS)
            self._increment(self._key(f"source_errors_5m", source), WINDOW_SECONDS)
            
        self._increment(self._key(f"source_events_5m", source), WINDOW_SECONDS)

        # Gets
        ip_count_5m = self._get(self._key("ip_count_5m", ip))
        ip_count_1m = self._get(self._key("ip_count_1m", ip))
        ip_fail_5m = self._get(self._key("ip_fail_5m", ip))
        
        global_events_5m = max(self._get(self._key("global_events_5m", "all")), 1)
        global_events_1m = self._get(self._key("global_events_1m", "all"))
        global_errors_5m = self._get(self._key("global_errors_5m", "all"))
        
        source_events_5m = max(self._get(self._key(f"source_events_5m", source)), 1)
        source_errors_5m = self._get(self._key(f"source_errors_5m", source))

        # Ratios
        source_error_rate_5m = source_errors_5m / source_events_5m
        ip_failure_ratio = ip_fail_5m / max(ip_count_5m, 1)
        global_error_ratio_5m = global_errors_5m / global_events_5m

        bytes_sent = float(self._safe_int(log.get("bytes")) or 0)
        
        entropy = self._shannon_entropy(message)
        has_error_kw = 1 if any(kw in message.lower() for kw in ["error", "fail", "deny", "crash"]) else 0
        has_crit_kw = 1 if any(kw in message.lower() for kw in ["oom", "panic", "corrupt", "killed"]) else 0
        
        features = [
            float(source_idx),
            float(source_error_rate_5m),
            float(source_events_5m),
            float(status or 0),
            float(1 if status and status >= 500 else 0),
            float(1 if status and 400 <= status < 500 else 0),
            bytes_sent,
            0.0, # bytes zscore stub
            float(ip_count_1m),
            float(ip_count_5m),
            float(ip_fail_5m),
            float(ip_failure_ratio),
            float(1 if ip_count_5m == 1 else 0), # ip_is_new
            float(1), # distinct users stub
            float(global_events_1m),
            float(global_events_5m),
            float(global_error_ratio_5m),
            float(hour),
            float(time.localtime().tm_wday),
            float(1 if hour < 7 or hour > 22 else 0), # off hours
            float(entropy),
            float(has_error_kw),
            float(has_crit_kw),
            float(sum(c.isdigit() for c in message)), # numeric token count stub
            float(1 if "auth_failure" in event_type else 0),
            float(ip_fail_5m) # consecutive failures stub
        ]
        
        return features

    @staticmethod
    def _safe_int(v) -> Optional[int]:
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
