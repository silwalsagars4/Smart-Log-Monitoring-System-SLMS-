"""
Docker collector — polls the Docker daemon for container log lines
using the official Docker SDK, avoids needing host file access.
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone

import docker
import redis

from collectors.base_collector import REDIS_STREAM, REDIS_MAXLEN

logger = logging.getLogger(__name__)


class DockerCollector:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def get_source(self) -> str:
        return "docker"

    def _tail_container(self, container):
        cname = container.name
        logger.info("[docker] Tailing container: %s", cname)
        try:
            for log_line in container.logs(stream=True, follow=True, timestamps=True):
                if self._stop_event.is_set():
                    break
                raw = log_line.decode("utf-8", errors="replace").strip()
                if not raw:
                    continue
                # Docker timestamps: 2024-01-15T12:00:00.000000000Z <message>
                parts = raw.split(" ", 1)
                ts = parts[0] if len(parts) > 1 else datetime.now(timezone.utc).isoformat()
                message = parts[1] if len(parts) > 1 else raw
                entry = {
                    "timestamp": ts,
                    "source": "docker",
                    "container": cname,
                    "message": message,
                    "raw": raw,
                }
                self.redis.xadd(
                    REDIS_STREAM,
                    {k: str(v) for k, v in entry.items()},
                    maxlen=REDIS_MAXLEN,
                    approximate=True,
                )
        except Exception as exc:
            logger.warning("[docker] Container %s ended: %s", cname, exc)

    def run(self):
        try:
            client = docker.from_env()
        except Exception as exc:
            logger.error("[docker] Cannot connect to Docker daemon: %s", exc)
            return

        known: set[str] = set()

        while not self._stop_event.is_set():
            try:
                containers = client.containers.list()
                for c in containers:
                    if c.id not in known:
                        known.add(c.id)
                        t = threading.Thread(target=self._tail_container, args=(c,), daemon=True)
                        t.start()
                        self._threads.append(t)
            except Exception as exc:
                logger.error("[docker] Error listing containers: %s", exc)
            time.sleep(10)

    def stop(self):
        self._stop_event.set()
