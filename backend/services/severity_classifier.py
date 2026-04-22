"""
Hybrid severity classifier.
Optimized for Baseline Stability.
"""

import re
from typing import NamedTuple


class SeverityResult(NamedTuple):
    severity: str
    reason: str


# Rule patterns  →  (severity, reason)
_RULES: list[tuple] = [
    # Disaster
    (re.compile(r"(OOMKilled|exited with code 137)", re.I), "disaster", "Container OOM killed"),
    (re.compile(r"(Disk full|No space left on device)", re.I), "disaster", "Disk full"),
    (re.compile(r"(crashed|Segmentation fault|kernel panic)", re.I), "disaster", "Process crashed"),
    (re.compile(r"(mysqld.*crash|InnoDB.*corrupt)", re.I), "disaster", "Database crash"),

    # High
    (re.compile(r"(Failed password for root|Invalid user root)", re.I), "high", "Root login attempt"),
    (re.compile(r"(sudo.*root|USER=root.*COMMAND)", re.I), "high", "Privilege escalation"),
    (re.compile(r"(Access denied for user.*root)", re.I), "high", "Root DB access denied"),
    (re.compile(r"status.*=?\s*5[0-9]{2}", re.I), "high", "HTTP 5xx server error"),

    # Medium
    (re.compile(r"(Failed password|authentication failure)", re.I), "medium", "Auth failure"),
    (re.compile(r"(Too many connections|max_connections)", re.I), "medium", "DB connection limit"),
    (re.compile(r"status.*=?\s*4[0-9]{2}", re.I), "medium", "HTTP 4xx client error"),

    # Warning
    (re.compile(r"(WARN|Warning|deprecated)", re.I), "warning", "Warning message"),
    (re.compile(r"(connection refused|timeout)", re.I), "warning", "Connection issue"),
]

# BASELINE: Explicitly "Normal" patterns that should rarely be upgraded
_SAFE_PATTERNS = re.compile(r"(GET /static/|HTTP/1.1\" 200|status=200|healthcheck|keepalive)", re.I)

_SEVERITY_ORDER = ["information", "warning", "medium", "high", "disaster"]

# INCREASED THRESHOLDS: ML now needs higher scores to upgrade severity
_ML_THRESHOLDS = [
    (0.95, "disaster"),
    (0.85, "high"),
    (0.75, "medium"),
    (0.60, "warning"),
]


def classify(log: dict, anomaly_score: float, is_anomaly: bool) -> SeverityResult:
    message = log.get("message", "") + " " + log.get("raw", "")
    event_type = log.get("event_type", "") or ""

    # 1. Check for explicit "Safe" patterns first (The Baseline)
    is_safe = bool(_SAFE_PATTERNS.search(message))

    # 2. Apply Rules — highest match wins
    rule_severity = "information"
    rule_reason = "Normal log entry"
    for pattern, sev, reason in _RULES:
        if pattern.search(message) or pattern.search(event_type):
            if _SEVERITY_ORDER.index(sev) > _SEVERITY_ORDER.index(rule_severity):
                rule_severity = sev
                rule_reason = reason

    # 3. ML Logic — only upgrades if it's NOT a safe pattern and score is high
    ml_severity = "information"
    ml_reason = ""
    
    # We only listen to the ML if the score is truly significant (>0.60)
    if is_anomaly and not is_safe:
        for threshold, sev in _ML_THRESHOLDS:
            if anomaly_score >= threshold:
                ml_severity = sev
                ml_reason = f"ML high-confidence anomaly (score={anomaly_score:.2f})"
                break

    # 4. Final Comparison
    # Take the higher of rule vs ML
    if _SEVERITY_ORDER.index(ml_severity) > _SEVERITY_ORDER.index(rule_severity):
        return SeverityResult(ml_severity, ml_reason)
    
    return SeverityResult(rule_severity, rule_reason)