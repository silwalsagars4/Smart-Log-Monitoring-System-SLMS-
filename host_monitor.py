import json
import time
import platform
import psutil
import redis
from datetime import datetime

# Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_KEY = 'slms:host_stats'
POLL_INTERVAL = 5

def get_service_status(name):
    """Simple process check for Windows services."""
    for proc in psutil.process_iter(['name']):
        try:
            if name.lower() in proc.info['name'].lower():
                return "Running"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return "Stopped"

def collect_host_stats():
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Memory
    mem = psutil.virtual_memory()
    
    # Disk
    disk = psutil.disk_usage('C:\\')
    
    # Swap
    swap = psutil.swap_memory()
    
    # Network
    net_io = psutil.net_io_counters()
    
    # Services (Common Windows names)
    watched = {
        "Docker": "docker",
        "PostgreSQL": "postgres",
        "Redis": "redis",
        "Nginx": "nginx",
        "MySQL": "mysqld"
    }
    services = {label: get_service_status(proc_name) for label, proc_name in watched.items()}

    return {
        "cpu_percent": cpu_percent,
        "mem_total_gb": round(mem.total / (1024**3), 2),
        "mem_used_gb": round(mem.used / (1024**3), 2),
        "mem_percent": mem.percent,
        "swap_total_gb": round(swap.total / (1024**3), 2),
        "swap_used_gb": round(swap.used / (1024**3), 2),
        "swap_percent": swap.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_percent": disk.percent,
        "os_name": f"Windows {platform.release()}",
        "os_version": platform.version(),
        "kernel": platform.machine(),
        "hostname": platform.node(),
        "uptime": time.time() - psutil.boot_time(),
        "process_count": len(psutil.pids()),
        "net_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
        "net_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
        "load_avg": [0, 0, 0], # Windows doesn't have load avg like Linux
        "services": services
    }

def main():
    try:
        import psutil
        import redis
    except ImportError:
        print("Error: Missing dependencies!")
        print("Please run: pip install psutil redis")
        return

    print(f"--- Native Windows Host Monitor ---")
    print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print("Connected successfully!")
    except Exception as e:
        print(f"\n[!] CONNECTION ERROR")
        print(f"Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT}.")
        print(f"1. Ensure 'docker compose up' is running.")
        print(f"2. Ensure you have restarted docker after the latest changes.")
        print(f"Details: {e}")
        return

    print(f"Monitoring {platform.node()}... Press Ctrl+C to stop.")
    
    try:
        while True:
            stats = collect_host_stats()
            r.set(REDIS_KEY, json.dumps(stats), ex=30)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Published Host Stats: CPU {stats['cpu_percent']}% | RAM {stats['mem_percent']}%")
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")

if __name__ == "__main__":
    main()
