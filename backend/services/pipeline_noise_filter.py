"""
Add this NOISE FILTER to your PipelineConsumer before logs hit the ML engine.

Find the method where you process each incoming log (likely called
`_process_log`, `process`, `handle_log`, or similar) and add the
is_noise() check as the FIRST thing before feature extraction or ML scoring.
"""

# ── Paste this block at the TOP of pipeline_consumer.py (after imports) ──────

import re as _re

# MongoDB internal message patterns — always safe, never score
_MONGO_MSG_NOISE = _re.compile(
    r"(Connection accepted|Connection ended|client metadata"
    r"|Connection not authenticating"
    r"|Received first command on ingress connection"
    r"|mongosh\s+\d+\.\d+\.\d+)",
    _re.I,
)

# MongoDB internal component/source identifiers
_MONGO_NOISE_SOURCES = frozenset({"NETWORK", "ACCESS", "CONTROL", "STORAGE", "REPL"})

# Docker healthcheck user agents / application names
_HEALTHCHECK_APPS = frozenset({"mongosh 2.8.2", "mongosh"})


def is_noise(log: dict) -> bool:
    """
    Returns True for logs that should be dropped before ML scoring.
    Covers:
      - MongoDB internal housekeeping (Docker healthcheck via mongosh)
      - Raw MongoDB structured log documents accidentally ingested
    """
    source = str(log.get("source", "")).upper()
    message = str(log.get("message", ""))
    raw = str(log.get("raw", ""))
    combined = message + " " + raw

    # MongoDB internal component source
    if any(noise in source for noise in _MONGO_NOISE_SOURCES):
        return True

    # MongoDB internal message pattern
    if _MONGO_MSG_NOISE.search(combined):
        return True

    # Raw MongoDB structured log leaked as string
    # e.g. "{'t': {'$date': ...}, 's': 'I', 'c': 'NETWORK', ...}"
    if "'$date'" in combined and ("'c': 'NETWORK'" in combined or '"c":"NETWORK"' in combined):
        return True

    # Docker healthcheck app
    attr_doc = log.get("attr", {}).get("doc", {})
    app_name = attr_doc.get("application", {}).get("name", "")
    if app_name in _HEALTHCHECK_APPS:
        return True

    return False


# ── In your process/consume method, add this BEFORE ML scoring ────────────────
#
# async def _process_log(self, log: dict):
#
#     # DROP noise before touching ML — kills false disaster alerts
#     if is_noise(log):
#         return
#
#     # ... rest of your existing feature extraction + ML scoring code
