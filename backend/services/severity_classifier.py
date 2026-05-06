"""
Hybrid severity classifier.
Optimized for Baseline Stability.
"""

import re
from typing import NamedTuple, Any


class SeverityResult(NamedTuple):
    severity: str
    reason: str
    insight: str = ""


class ContextualInterpreter:
    def __init__(self):
        self._patterns = [
            (re.compile(r"status.*=?\s*5[0-9]{2}", re.I), "Server-side error. Investigate application logs for stack traces."),
            (re.compile(r"status.*=?\s*401", re.I), "Authentication credentials missing or invalid."),
            (re.compile(r"status.*=?\s*403", re.I), "Authenticated user lacks permission for this resource."),
            (re.compile(r"Access denied for user.*root", re.I), "MySQL root credentials incorrect or lacking GRANT privileges."),
            (re.compile(r"error 1045", re.I), "MySQL error 1045: Access denied. Check DB credentials."),
            (re.compile(r"Too many connections", re.I), "MySQL connection pool exhausted. Increase max_connections."),
            (re.compile(r"Connection refused", re.I), "Target service not listening. Check if the process is running."),
            (re.compile(r"OOMKilled|exit code 137", re.I), "Container killed by OOM manager. Increase memory limits."),
            (re.compile(r"No space left", re.I), "Filesystem 100% full. Services will fail until space is freed."),
            (re.compile(r"Failed password for root", re.I), "SSH brute-force on root detected. Consider fail2ban."),
            (re.compile(r"Segmentation fault", re.I), "Process crashed — illegal memory access or memory corruption."),
            (re.compile(r"Invalid user", re.I), "SSH login for non-existent user. Likely automated scanning."),
        ]

    def interpret(self, message: str) -> str:
        for pattern, insight in self._patterns:
            if pattern.search(message):
                return insight
        return ""

_interpreter = ContextualInterpreter()


# Rule patterns  →  (severity, reason)
_RULES: list[tuple] = [
    # Disaster
    (re.compile(r"(OOMKilled|exited with code 137)", re.I), "disaster", "Container OOM killed"),
    (re.compile(r"(Disk full|No space left on device)", re.I), "disaster", "Disk full"),
    (re.compile(r"(crashed|Segmentation fault|kernel panic)", re.I), "disaster", "Process crashed"),
    (re.compile(r"(mysqld.*crash|InnoDB.*corrupt)", re.I), "disaster", "Database crash"),
    (re.compile(r"(Failed password for root|Invalid user root|Access denied for user.*root)", re.I), "disaster", "Critical Auth Failure (Root)"),
    (re.compile(r"(stopped|restarted|shutting down|sigterm)", re.I), "disaster", "Service Lifecycle Event"),

    # High
    (re.compile(r"(sudo.*root|USER=root.*COMMAND)", re.I), "high", "Privilege escalation"),
    (re.compile(r"status.*=?\s*5[0-9]{2}", re.I), "high", "HTTP 5xx server error"),

    # Medium
    (re.compile(r"(Failed password|authentication failure)", re.I), "medium", "Auth failure"),

    (re.compile(r"(Too many connections|max_connections)", re.I), "medium", "DB connection limit"),
    (re.compile(r"status.*=?\s*4[0-9]{2}", re.I), "medium", "HTTP 4xx client error"),

    # Warning
    (re.compile(r"(WARN|Warning|deprecated)", re.I), "warning", "Warning message"),
    (re.compile(r"(connection refused|timeout)", re.I), "warning", "Connection issue"),
]

# ── Noise / Safe patterns ─────────────────────────────────────────────────────
# Logs matching these are NEVER upgraded by ML — they are baseline normal traffic.

_SAFE_PATTERNS = re.compile(
    r"("
    # HTTP baseline
    r"GET /(static|assets)/|HTTP/1\.[01]\" (200|304|204)|status=(200|304|204)|healthcheck|keepalive"
    # MongoDB internal housekeeping (Docker healthcheck via mongosh)
    r"|Connection accepted|Connection ended|client metadata"
    r"|Connection not authenticating"
    r"|Received first command on ingress connection"
    r"|mongosh\s+\d+\.\d+\.\d+"
    r")",
    re.I,
)


# MongoDB source/component identifiers that are always internal noise
_MONGO_NOISE_SOURCES = {"NETWORK", "ACCESS", "CONTROL", "STORAGE", "REPL"}

_SEVERITY_ORDER = ["information", "warning", "medium", "high", "disaster"]

# INCREASED THRESHOLDS: ML now needs higher scores to upgrade severity
_ML_THRESHOLDS = [
    (0.95, "disaster"),
    (0.85, "high"),
    (0.75, "medium"),
    (0.60, "warning"),
]


def _is_mongo_internal(log: dict) -> bool:
    """
    Returns True for MongoDB internal logs that should never be ML-scored.
    These arrive as raw MongoDB structured log documents ingested directly
    from the mongo container (healthcheck pings via mongosh).
    """
    source = str(log.get("source", "")).upper()
    message = str(log.get("message", ""))

    # Source component is a known MongoDB-internal component
    if any(noise in source for noise in _MONGO_NOISE_SOURCES):
        return True

    # The raw message is a MongoDB structured log dict stringified
    # e.g. "{'t': {'$date': ...}, 's': 'I', 'c': 'NETWORK', ...}"
    if "'$date'" in message and "'c': 'NETWORK'" in message:
        return True

    return False


def classify(log: dict, ml_result: Any) -> SeverityResult:
    """
    Layered Consensus Engine.
    Combines Heuristic Rules, Supervised Text ML, and Unsupervised Structural ML.
    """
    message = str(log.get("message", "")) + " " + str(log.get("raw", ""))
    event_type = log.get("event_type", "") or ""

    # 0. Skip Noise (e.g. MongoDB internal)
    if _is_mongo_internal(log):
        return SeverityResult("information", "Internal noise (filtered)", "")

    # 1. Baseline: Check for explicit "Safe" patterns
    is_safe = bool(_SAFE_PATTERNS.search(message))

    # 2. Layer 1: Deterministic Rules (Highest Precision)
    rule_severity = "information"
    rule_reason = "No matching rules"
    for pattern, sev, reason in _RULES:
        if pattern.search(message) or pattern.search(event_type):
            if _SEVERITY_ORDER.index(sev) > _SEVERITY_ORDER.index(rule_severity):
                rule_severity = sev
                rule_reason = reason

    # 3. Layer 2 & 3: ML Consensus
    # ml_result is a SmartMLEngine.MLResult object
    score = ml_result.score
    is_anomaly = ml_result.is_anomaly
    sup_sev = ml_result.supervised_sev
    sup_conf = ml_result.supervised_conf

    ml_severity = "information"
    ml_reason = ""

    # If the supervised model is VERY confident, it takes priority over anomaly score
    if sup_conf > 0.85:
        ml_severity = sup_sev
        ml_reason = f"Supervised ML high-confidence {sup_sev}"
    elif is_anomaly and not is_safe:
        # Fallback to anomaly-based severity if supervised is unsure
        for threshold, sev in _ML_THRESHOLDS:
            if score >= threshold:
                ml_severity = sev
                ml_reason = f"Anomaly-detected {sev} (score={score:.2f})"
                break
        
        # Cross-check: If anomaly says disaster but supervised says information, 
        # downgrade to warning unless a hard rule says otherwise.
        if ml_severity == "disaster" and sup_sev == "information" and sup_conf > 0.6:
            ml_severity = "warning"
            ml_reason = "Novel pattern flagged as warning (structural anomaly but safe text)"

    # 4. Final Aggregation (Highest Wins, but rules can be overridden by high-conf ML)
    # Exception: If a Rule says Disaster (OOM, Crash), we never downgrade it.
    final_severity = rule_severity
    final_reason = rule_reason
    
    rule_idx = _SEVERITY_ORDER.index(rule_severity)
    ml_idx = _SEVERITY_ORDER.index(ml_severity)

    if ml_idx > rule_idx:
        # Upgrade to ML severity if it's higher
        final_severity = ml_severity
        final_reason = ml_reason
    elif rule_idx > ml_idx and rule_severity == "disaster":
        # Keep Disaster if rule detected it
        final_severity = "disaster"
        final_reason = rule_reason

    # 5. Insight Generation
    insight = _interpreter.interpret(message)

    # 6. Final Anomaly Override
    # If the final severity is information or it's a known safe pattern, 
    # we force is_anomaly to False to ensure it doesn't skew stats.
    final_is_anomaly = is_anomaly
    if final_severity == "information" or is_safe:
        final_is_anomaly = False

    return SeverityResult(final_severity, final_reason, insight), final_is_anomaly


