"""
Base log collector — tail-F style reader with log rotation support.
Each subclass overrides `get_source()` and uses the parser registry.
"""

import os
import time
import json
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import redis

logger = logging.getLogger(__name__)

REDIS_STREAM = "slms:logs"
REDIS_MAXLEN = 50_000  # cap stream length


class BaseCollector(ABC):
    def __init__(self, file_path: str, redis_client: redis.Redis, parser, poll_interval: float = 0.1):
        self.file_path = file_path
        self.redis = redis_client
        self.parser = parser
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()

    @abstractmethod
    def get_source(self) -> str:
        """Return the log source name, e.g. 'ssh', 'nginx'."""

    def publish(self, raw_line: str):
        """Parse a raw log line and push structured entry to Redis Stream."""
        raw_line = raw_line.strip()
        if not raw_line:
            return
        try:
            structured = self.parser.parse(raw_line)
            if structured is None:
                # Priority: regex fallback → collector metadata
                from parsers.source_detector import detect_source
                detected = detect_source(raw_line)
                structured = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": detected if detected != "unknown" else self.get_source(),
                    "raw": raw_line,
                    "message": raw_line,
                    "event_type": "unparsed",
                }
            # Collector source is the authoritative final stamp only if parser didn't set one
            structured.setdefault("source", self.get_source())
            structured.setdefault("raw", raw_line)
            self.redis.xadd(
                REDIS_STREAM,
                {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in structured.items()},
                maxlen=REDIS_MAXLEN,
                approximate=True,
            )
        except Exception as exc:
            logger.warning("Failed to publish log line: %s — %s", raw_line[:120], exc)

    def _get_inode(self) -> int | None:
        try:
            return os.stat(self.file_path).st_ino
        except OSError:
            return None

    def run(self):
        """Main loop — tail the file, handle rotation gracefully."""
        logger.info("[%s] Starting collector on %s", self.get_source(), self.file_path)
        fh = None
        current_inode = None

        while not self._stop_event.is_set():
            try:
                if not os.path.exists(self.file_path):
                    logger.debug("[%s] Waiting for log file to appear…", self.get_source())
                    time.sleep(2)
                    continue

                new_inode = self._get_inode()

                if fh is None or new_inode != current_inode:
                    if fh:
                        fh.close()
                    fh = open(self.file_path, "r", encoding="utf-8", errors="replace")
                    fh.seek(0, 2)  # seek to EOF
                    current_inode = new_inode
                    logger.info("[%s] (Re)opened %s", self.get_source(), self.file_path)

                line = fh.readline()
                if line:
                    self.publish(line)
                else:
                    time.sleep(self.poll_interval)

            except Exception as exc:
                logger.error("[%s] Collector error: %s", self.get_source(), exc)
                if fh:
                    fh.close()
                    fh = None
                time.sleep(5)

    def stop(self):
        self._stop_event.set()
