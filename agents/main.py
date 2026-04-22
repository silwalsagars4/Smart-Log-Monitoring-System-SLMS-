"""
Agent orchestrator — spawns all collectors in threads and keeps them alive.
"""

import logging
import signal
import sys
import threading
import os
from dotenv import load_dotenv

import redis as redis_lib

from collectors.ssh_collector import SSHCollector
from collectors.nginx_collector import NginxCollector
from collectors.apache_collector import ApacheCollector
from collectors.docker_collector import DockerCollector
from collectors.mysql_collector import MySQLCollector

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agents.main")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def build_redis() -> redis_lib.Redis:
    return redis_lib.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=10)


def main():
    r = build_redis()
    try:
        r.ping()
        logger.info("Connected to Redis at %s", REDIS_URL)
    except Exception as exc:
        logger.error("Cannot connect to Redis: %s", exc)
        sys.exit(1)

    collectors = [
        SSHCollector(r),
        NginxCollector(r),
        ApacheCollector(r),
        MySQLCollector(r),
        DockerCollector(r),
    ]

    threads = []
    for col in collectors:
        t = threading.Thread(target=col.run, name=col.get_source(), daemon=True)
        t.start()
        threads.append((t, col))
        logger.info("Started collector: %s", col.get_source())

    def _shutdown(sig, frame):
        logger.info("Shutdown signal received. Stopping collectors…")
        for _, col in threads:
            col.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Keep main thread alive
    for t, _ in threads:
        t.join()


if __name__ == "__main__":
    main()
