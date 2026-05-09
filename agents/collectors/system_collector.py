"""
SystemCollector — gathers hardware & OS telemetry and publishes it
to the Redis key  slms:system_stats  as a JSON string every 5 seconds.

Mounted host paths expected (read-only):
  /host/proc  → from host /proc
  /host/sys   → from host /sys
  /host/etc/os-release → from host /etc/os-release
"""

import json
import logging
import os
import platform
import threading
import time

import psutil
import redis

logger = logging.getLogger(__name__)

REDIS_KEY       = "slms:system_stats"
POLL_INTERVAL   = 5          # seconds
OS_RELEASE_PATH = os.getenv("HOST_OS_RELEASE", "/host/etc/os-release")

# Services to probe (name as systemd would report it, without .service suffix)
WATCHED_SERVICES = ["sshd", "docker", "nginx", "apache2", "mysql", "postgresql"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_os_release(path: str) -> dict:
    """Parse /etc/os-release (or its host-mounted equivalent)."""
    info = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    info[k.strip()] = v.strip().strip('"')
    except Exception as exc:
        logger.debug("Cannot read os-release at %s: %s", path, exc)
    return info


def _service_status(name: str) -> str:
    """
    Check whether a process matching *name* is running.
    Uses psutil — does NOT require systemd or root.
    Returns 'Running' or 'Stopped'.
    """
    try:
        for proc in psutil.process_iter(["name", "status"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                if name.lower() in pname and proc.info.get("status") != psutil.STATUS_ZOMBIE:
                    return "Running"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as exc:
        logger.debug("Service probe failed for %s: %s", name, exc)
    return "Stopped"


def _collect() -> dict:
    """Assemble one snapshot of system metrics. All reads are try-except guarded."""

    # ── CPU ──────────────────────────────────────────────────────────────────
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
    except Exception:
        cpu_percent = 0.0

    # ── Memory ───────────────────────────────────────────────────────────────
    try:
        mem = psutil.virtual_memory()
        mem_total_gb  = round(mem.total  / (1024 ** 3), 2)
        mem_used_gb   = round(mem.used   / (1024 ** 3), 2)
        mem_percent   = mem.percent
    except Exception:
        mem_total_gb = mem_used_gb = mem_percent = 0.0

    # ── Disk (root partition) ─────────────────────────────────────────────────
    try:
        disk = psutil.disk_usage("/")
        disk_total_gb = round(disk.total / (1024 ** 3), 2)
        disk_used_gb  = round(disk.used  / (1024 ** 3), 2)
        disk_percent  = disk.percent
    except Exception:
        disk_total_gb = disk_used_gb = disk_percent = 0.0

    # ── OS Info ───────────────────────────────────────────────────────────────
    try:
        os_release = _parse_os_release(OS_RELEASE_PATH)
        os_name    = os_release.get("PRETTY_NAME") or os_release.get("NAME", platform.system())
        os_version = os_release.get("VERSION_ID", platform.version())
    except Exception:
        os_name    = platform.system()
        os_version = platform.version()

    try:
        kernel = platform.release()
        # If running on Windows host via Docker Desktop/WSL2, kernel often contains 'microsoft'
        if "microsoft" in kernel.lower() or "wsl" in kernel.lower():
            os_name = f"Windows (via {os_name})"
    except Exception:
        kernel = "unknown"

    try:
        if os.path.exists("/host/etc/hostname"):
            with open("/host/etc/hostname", "r") as f:
                hostname = f.read().strip()
        else:
            hostname = platform.node()
    except Exception:
        hostname = "unknown"

    # ── Extended Stats ────────────────────────────────────────────────────────
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        process_count  = len(psutil.pids())
        net_io = psutil.net_io_counters()
        net_sent_mb = round(net_io.bytes_sent / (1024 * 1024), 2)
        net_recv_mb = round(net_io.bytes_recv / (1024 * 1024), 2)
        
        # Load average (1, 5, 15 min)
        load_1, load_5, load_15 = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
        
        # Swap memory
        swap = psutil.swap_memory()
        swap_percent = swap.percent
        swap_total_gb = round(swap.total / (1024 ** 3), 2)
        swap_used_gb = round(swap.used / (1024 ** 3), 2)
        
    except Exception:
        uptime_seconds = 0
        process_count  = 0
        net_sent_mb = net_recv_mb = 0.0
        load_1 = load_5 = load_15 = 0.0
        swap_percent = 0.0
        swap_total_gb = swap_used_gb = 0.0

    # ── Services ──────────────────────────────────────────────────────────────
    services = {}
    for svc in WATCHED_SERVICES:
        try:
            services[svc] = _service_status(svc)
        except Exception:
            services[svc] = "Stopped"

    return {
        "cpu_percent":    cpu_percent,
        "mem_total_gb":   mem_total_gb,
        "mem_used_gb":    mem_used_gb,
        "mem_percent":    mem_percent,
        "swap_total_gb":  swap_total_gb,
        "swap_used_gb":   swap_used_gb,
        "swap_percent":   swap_percent,
        "disk_total_gb":  disk_total_gb,
        "disk_used_gb":   disk_used_gb,
        "disk_percent":   disk_percent,
        "os_name":        os_name,
        "os_version":     os_version,
        "kernel":         kernel,
        "hostname":       hostname,
        "uptime":         uptime_seconds,
        "process_count":  process_count,
        "net_sent_mb":    net_sent_mb,
        "net_recv_mb":    net_recv_mb,
        "load_avg":       [load_1, load_5, load_15],
        "services":       services,
    }


# ── Collector Thread ──────────────────────────────────────────────────────────

class SystemCollector(threading.Thread):
    """
    Background thread that publishes system telemetry to Redis every
    POLL_INTERVAL seconds.  Non-fatal errors are logged and silently skipped
    so the thread never crashes the agent process.
    """

    def __init__(self, redis_client: redis.Redis):
        super().__init__(daemon=True, name="SystemCollector")
        self.redis = redis_client
        self._stop_event = threading.Event()

    def run(self):
        logger.info("SystemCollector started — publishing to %s every %ds", REDIS_KEY, POLL_INTERVAL)
        while not self._stop_event.is_set():
            try:
                snapshot = _collect()
                self.redis.set(REDIS_KEY, json.dumps(snapshot), ex=30)  # TTL 30 s
                logger.debug("SystemCollector published snapshot: cpu=%.1f%%", snapshot["cpu_percent"])
            except Exception as exc:
                logger.warning("SystemCollector publish error: %s", exc)

            # Sleep in small chunks so stop() responds quickly
            for _ in range(POLL_INTERVAL * 10):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)

    def stop(self):
        self._stop_event.set()
