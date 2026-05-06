"""
Agent orchestrator — spawns all collectors in threads and keeps them alive.
Supports dynamic log configuration via ConfigWatcher.
"""

import logging
import signal
import sys
import threading
import time
import os
import requests
from dotenv import load_dotenv

import redis as redis_lib

from collectors.ssh_collector import SSHCollector
from collectors.nginx_collector import NginxCollector
from collectors.apache_collector import ApacheCollector
from collectors.docker_collector import DockerCollector
from collectors.mysql_collector import MySQLCollector
from collectors.generic_collector import GenericCollector

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agents.main")

REDIS_URL    = os.getenv("REDIS_URL",    "redis://localhost:6379")
BACKEND_URL  = os.getenv("BACKEND_URL",  "http://localhost:8000")

# ── Excluded containers ───────────────────────────────────────────────────────
# SLMS own infrastructure — never monitor these.
# Tailing them causes the ML to score healthy startup/auth logs as disaster
# because they look nothing like the HTTP/SSH bootstrap training data.
EXCLUDED_CONTAINERS = {
    "slms-backend",
    "slms-frontend",
    "slms-mongo",
    "slms-redis",
    "slms-postgres",
    "slms-agents",
}


def build_redis() -> redis_lib.Redis:
    return redis_lib.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=10)


class ConfigWatcher(threading.Thread):
    def __init__(self, redis_client: redis_lib.Redis):
        super().__init__(daemon=True, name="ConfigWatcher")
        self.redis = redis_client
        self._stop_event = threading.Event()
        self.active_collectors: dict[int, tuple[threading.Thread, GenericCollector]] = {}

    def run(self):
        logger.info("ConfigWatcher started. Polling %s/api/config/log-paths", BACKEND_URL)
        while not self._stop_event.is_set():
            try:
                resp = requests.get(f"{BACKEND_URL}/api/config/log-paths", timeout=5)
                if resp.status_code == 200:
                    configs = resp.json()
                    self._sync_collectors(configs)
            except Exception as exc:
                logger.debug("Failed to fetch log configs (backend down?): %s", exc)

            for _ in range(30):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _sync_collectors(self, configs: list[dict]):
        active_ids = set()

        for cfg in configs:
            if not cfg.get("is_active"):
                continue

            cfg_id = cfg["id"]
            active_ids.add(cfg_id)

            if cfg_id not in self.active_collectors:
                log_path = cfg["log_path"]
                if log_path.startswith("/var/") and not log_path.startswith("/host/var/"):
                    log_path = f"/host{log_path}"
                elif log_path.startswith("/opt/") and not log_path.startswith("/host/opt/"):
                    log_path = f"/host{log_path}"

                col = GenericCollector(
                    log_path=log_path,
                    collector_type=cfg["collector_type"],
                    redis_client=self.redis,
                    config_id=cfg_id,
                    label=cfg["label"]
                )
                t = threading.Thread(
                    target=col.run,
                    name=f"Dynamic-{cfg['collector_type']}-{cfg_id}",
                    daemon=True,
                )
                t.start()
                self.active_collectors[cfg_id] = (t, col)
                logger.info(
                    "Started dynamic collector for config %d (%s)",
                    cfg_id, cfg["log_path"],
                )

        current_ids = set(self.active_collectors.keys())
        for removed_id in current_ids - active_ids:
            t, col = self.active_collectors[removed_id]
            logger.info("Stopping dynamic collector for config %d", removed_id)
            col.stop()
            del self.active_collectors[removed_id]

    def stop(self):
        self._stop_event.set()
        for t, col in self.active_collectors.values():
            col.stop()


def main():
    r = build_redis()
    try:
        r.ping()
        logger.info("Connected to Redis at %s", REDIS_URL)
    except Exception as exc:
        logger.error("Cannot connect to Redis: %s", exc)
        sys.exit(1)

    static_collectors = [
        SSHCollector(r),
        NginxCollector(r),
        ApacheCollector(r),
        MySQLCollector(r),
        # FIX: pass excluded_containers so the collector never tails SLMS
        # infrastructure — tailing our own containers caused every healthy
        # startup/auth log to score 1.000 disaster by the ML ensemble.
        DockerCollector(r, excluded_containers=EXCLUDED_CONTAINERS),
    ]

    threads = []
    for col in static_collectors:
        t = threading.Thread(target=col.run, name=col.get_source(), daemon=True)
        t.start()
        threads.append((t, col))
        logger.info("Started static collector: %s", col.get_source())

    watcher = ConfigWatcher(r)
    watcher.start()

    def _shutdown(sig, frame):
        logger.info("Shutdown signal received. Stopping collectors…")
        watcher.stop()
        for _, col in threads:
            col.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    for t, _ in threads:
        t.join()
    watcher.join()


if __name__ == "__main__":
    main()
