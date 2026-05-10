"""
SLMS Dual-Mode Log Simulator
Modes:
  - train: Generates 95% "Normal" traffic to build a baseline for the ML.
  - attack: Generates heavy anomalies and security threats.
"""

import argparse
import json
import os
import random
import time
from datetime import datetime, timezone, timedelta

import redis as redis_lib
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_STREAM = "slms:logs"

# Configuration Data
FAKE_IPS = ["192.168.1.100", "10.0.0.5", "172.16.0.22", "45.33.32.156", "1.2.3.4", "5.6.7.8"]
USERNAMES = ["root", "admin", "ubuntu", "sagar"]
NGINX_PATHS = ["/", "/api/v1/health", "/api/v1/logs", "/dashboard", "/login"]

def now_iso() -> str:
    # Kathmandu is UTC +5:45
    tz_kathmandu = timezone(timedelta(hours=5, minutes=45))
    return datetime.now(tz_kathmandu).isoformat()

# --- LOG GENERATORS ---

def gen_normal_traffic(r: redis_lib.Redis):
    """Generates a standard HTTP 200 OK log."""
    ip = random.choice(FAKE_IPS)
    path = random.choice(NGINX_PATHS)
    entry = {
        "timestamp": now_iso(),
        "source": "nginx",
        "event_type": "http_request",
        "ip": ip,
        "method": "GET",
        "path": path,
        "status": "200",
        "message": f"GET {path} → 200",
        "raw": f'{ip} - - [{now_iso()}] "GET {path} HTTP/1.1" 200 {random.randint(500, 1500)}',
    }
    r.xadd(REDIS_STREAM, entry, maxlen=50000, approximate=True)

def gen_ssh_failure(r: redis_lib.Redis):
    ip = random.choice(FAKE_IPS)
    user = random.choice(USERNAMES)
    entry = {
        "timestamp": now_iso(),
        "source": "ssh",
        "event_type": "auth_failure",
        "user": user,
        "ip": ip,
        "message": f"Failed password for {user} from {ip}",
        "raw": f"Apr 23 10:22:01 host sshd: Failed password for {user} from {ip} port 22 ssh2",
    }
    r.xadd(REDIS_STREAM, entry, maxlen=50000, approximate=True)

def gen_attack_burst(r: redis_lib.Redis):
    """Simulates a rapid-fire brute force attack."""
    ip = "91.108.4.1" # Fixed attacker IP
    for _ in range(random.randint(10, 20)):
        gen_ssh_failure(r)
        time.sleep(0.01)

def gen_critical_error(r: redis_lib.Redis):
    """Simulates a database or system crash."""
    errors = ["Disk full (/tmp)", "InnoDB: Cannot allocate memory", "Segmentation fault"]
    msg = random.choice(errors)
    entry = {
        "timestamp": now_iso(),
        "source": "system",
        "event_type": "critical_error",
        "message": msg,
        "raw": f"CRITICAL: {msg}",
    }
    r.xadd(REDIS_STREAM, entry, maxlen=50000, approximate=True)

# --- SCENARIOS ---

# Train Mode: Mostly 200 OKs, very few errors
TRAIN_SCENARIOS = [
    (gen_normal_traffic, 0.95),
    (gen_ssh_failure, 0.05),
]

# Attack Mode: High volume of failures and crashes
ATTACK_SCENARIOS = [
    (gen_normal_traffic, 0.20),
    (gen_ssh_failure, 0.30),
    (gen_attack_burst, 0.25),
    (gen_critical_error, 0.25),
]

def simulate(mode: str, rate: float, duration: int):
    r = redis_lib.from_url(REDIS_URL, decode_responses=True)
    scenarios = TRAIN_SCENARIOS if mode == "train" else ATTACK_SCENARIOS
    
    print(f"🚀 MODE: {mode.upper()} | Rate: {rate}/s | Duration: {duration}s")
    
    end = time.time() + duration
    while time.time() < end:
        roll = random.random()
        cumulative = 0.0
        for fn, prob in scenarios:
            cumulative += prob
            if roll < cumulative:
                fn(r)
                break
        time.sleep(1.0 / rate)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train", "attack"], default="train")
    parser.add_argument("--rate", type=float, default=10.0)
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()
    simulate(args.mode, args.rate, args.duration)