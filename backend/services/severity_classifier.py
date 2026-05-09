"""
Hybrid Severity Classifier — Enhanced Layered Consensus Engine.

Improvements over v1:
  - FrequencyAnalyzer: sliding-window burst detection per IP/source/event-type
  - Confidence-weighted voting instead of naive "highest wins"
  - Rule confidence scores: not every rule match carries equal weight
  - Temporal correlation: repeated events in a short window escalate severity
  - Expanded rule set covering more attack/failure signatures
  - Graduated safe-pattern dampening instead of binary suppression
  - Structured SeverityResult with richer metadata for downstream consumers
"""

import re
import time
from collections import defaultdict, deque
from typing import Any, NamedTuple

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# Return type
# ──────────────────────────────────────────────────────────────────────────────

class SeverityResult(NamedTuple):
    severity: str
    reason: str
    insight: str = ""
    # NEW fields
    rule_confidence: float = 0.0    # [0,1] how confident the winning rule is
    frequency_factor: float = 0.0   # [0,1] burst/repeat boost applied
    final_score: float = 0.0        # composite score used for the decision


# ──────────────────────────────────────────────────────────────────────────────
# Contextual Insight Generator (unchanged interface, extended patterns)
# ──────────────────────────────────────────────────────────────────────────────

class ContextualInterpreter:
    def __init__(self):
        self._patterns = [
            (re.compile(r"status.*=?\s*5[0-9]{2}", re.I),
             "Server-side error. Investigate application logs for stack traces."),
            (re.compile(r"status.*=?\s*401", re.I),
             "Authentication credentials missing or invalid."),
            (re.compile(r"status.*=?\s*403", re.I),
             "Authenticated user lacks permission for this resource."),
            (re.compile(r"Access denied for user.*root", re.I),
             "MySQL root credentials incorrect or lacking GRANT privileges."),
            (re.compile(r"error 1045", re.I),
             "MySQL error 1045: Access denied. Check DB credentials."),
            (re.compile(r"Too many connections", re.I),
             "MySQL connection pool exhausted. Increase max_connections."),
            (re.compile(r"Connection refused", re.I),
             "Target service not listening. Check if the process is running."),
            (re.compile(r"OOMKilled|exit code 137", re.I),
             "Container killed by OOM manager. Increase memory limits."),
            (re.compile(r"No space left", re.I),
             "Filesystem 100% full. Services will fail until space is freed."),
            (re.compile(r"Failed password for root", re.I),
             "SSH brute-force on root detected. Consider fail2ban."),
            (re.compile(r"Segmentation fault", re.I),
             "Process crashed — illegal memory access or memory corruption."),
            (re.compile(r"Invalid user", re.I),
             "SSH login for non-existent user. Likely automated scanning."),
            # Extended patterns
            (re.compile(r"SSL.*handshake.*fail|certificate.*expir", re.I),
             "TLS/SSL failure. Check certificate validity and chain of trust."),
            (re.compile(r"Killed process|oom.killer", re.I),
             "Linux OOM killer fired. Review container memory limits and cgroup settings."),
            (re.compile(r"ECONNRESET|connection reset by peer", re.I),
             "Connection reset mid-stream. Could indicate firewall rule or upstream crash."),
            (re.compile(r"ETIMEDOUT|operation timed out", re.I),
             "Network timeout. Check upstream service health and DNS resolution."),
            (re.compile(r"permission denied.*\/etc\/(shadow|passwd|sudoers)", re.I),
             "Suspicious access to sensitive system files. Investigate immediately."),
            (re.compile(r"exec.*\/bin\/(bash|sh)|\/bin\/sh.*-i", re.I),
             "Shell spawn detected in log. Possible command injection or reverse shell."),
            (re.compile(r"curl.*\|\s*bash|wget.*\|\s*sh", re.I),
             "Pipe-to-shell pattern detected — potential dropper or supply chain attack."),
            (re.compile(r"READONLY.*innodb|table.*is.*read.only", re.I),
             "InnoDB in read-only mode. Check for filesystem errors or crash recovery."),
        ]

    def interpret(self, message: str) -> str:
        for pattern, insight in self._patterns:
            if pattern.search(message):
                return insight
        return ""


_interpreter = ContextualInterpreter()


# ──────────────────────────────────────────────────────────────────────────────
# Rule definitions
# Each entry: (compiled_regex, severity, reason, confidence)
# confidence reflects how reliably this pattern indicates the stated severity.
# ──────────────────────────────────────────────────────────────────────────────

_RULES: list[tuple] = [
    # ── Disaster (confidence 0.95–1.0) ──────────────────────────────────────
    (re.compile(r"(OOMKilled|exited with code 137)", re.I),
     "disaster", "Container OOM killed", 1.0),
    (re.compile(r"(Disk full|No space left on device)", re.I),
     "disaster", "Disk full", 1.0),
    (re.compile(r"(crashed|Segmentation fault|kernel panic)", re.I),
     "disaster", "Process crashed", 0.97),
    (re.compile(r"(mysqld.*crash|InnoDB.*corrupt)", re.I),
     "disaster", "Database crash/corruption", 0.99),
    (re.compile(r"(Failed password for root|Invalid user root|Access denied for user.*root)", re.I),
     "disaster", "Critical auth failure (root)", 0.95),
    (re.compile(r"(service.*stopped|restarted.*error|shutting down.*error|sigterm)", re.I),
     "disaster", "Service lifecycle error event", 0.90),
    (re.compile(r"(exec.*\/bin\/(bash|sh)|\/bin\/sh.*-i)", re.I),
     "disaster", "Shell spawn / possible RCE", 0.98),
    (re.compile(r"(curl.*\|\s*bash|wget.*\|\s*sh)", re.I),
     "disaster", "Dropper / pipe-to-shell pattern", 0.99),
    (re.compile(r"(Killed process.*oom|oom.killer.*killed)", re.I),
     "disaster", "OOM killer fired", 0.96),

    # ── High (confidence 0.80–0.94) ─────────────────────────────────────────
    (re.compile(r"(sudo.*root|USER=root.*COMMAND)", re.I),
     "high", "Privilege escalation", 0.90),
    (re.compile(r"status.*=?\s*5[0-9]{2}", re.I),
     "high", "HTTP 5xx server error", 0.85),
    (re.compile(r"(SSL.*handshake.*fail|certificate.*expir)", re.I),
     "high", "TLS/SSL failure", 0.88),
    (re.compile(r"(ECONNRESET|connection reset by peer)", re.I),
     "high", "Unexpected connection reset", 0.80),
    (re.compile(r"(permission denied.*\/etc\/(shadow|passwd|sudoers))", re.I),
     "high", "Sensitive file access denied", 0.93),

    # ── Medium (confidence 0.65–0.79) ────────────────────────────────────────
    (re.compile(r"(Failed password|authentication failure)", re.I),
     "medium", "Auth failure", 0.72),
    (re.compile(r"(Too many connections|max_connections)", re.I),
     "medium", "DB connection limit", 0.78),
    (re.compile(r"status.*=?\s*4[0-9]{2}", re.I),
     "medium", "HTTP 4xx client error", 0.65),
    (re.compile(r"(ETIMEDOUT|operation timed out)", re.I),
     "medium", "Network timeout", 0.70),
    (re.compile(r"(READONLY.*innodb|table.*is.*read.only)", re.I),
     "medium", "DB read-only mode", 0.76),

    # ── Warning (confidence 0.50–0.64) ───────────────────────────────────────
    (re.compile(r"(WARN|Warning|deprecated)", re.I),
     "warning", "Warning message", 0.55),
    (re.compile(r"(connection refused|timeout)", re.I),
     "warning", "Connection issue", 0.58),
    (re.compile(r"(retry|retrying|backoff)", re.I),
     "warning", "Retry/backoff detected", 0.52),
]


# ──────────────────────────────────────────────────────────────────────────────
# Safe / noise patterns
# ──────────────────────────────────────────────────────────────────────────────

_SAFE_PATTERNS = re.compile(
    r"("
    r"GET /(static|assets)/|HTTP/1\.[01]\" (200|304|204)|status=(200|304|204)|healthcheck|keepalive"
    r"|Connection accepted|Connection ended|client metadata"
    r"|Connection not authenticating"
    r"|Received first command on ingress connection"
    r"|mongosh\s+\d+\.\d+\.\d+"
    r")",
    re.I,
)

_MONGO_NOISE_SOURCES = {"NETWORK", "ACCESS", "CONTROL", "STORAGE", "REPL"}

_SEVERITY_ORDER = ["information", "warning", "medium", "high", "disaster"]

# Score addend applied when upgrading via ML anomaly (raised thresholds vs v1)
_ML_THRESHOLDS = [
    (0.95, "disaster"),
    (0.85, "high"),
    (0.75, "medium"),
    (0.60, "warning"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Frequency Analyzer
# Replaces the hardcoded ip_fail_5m check in the old smart_ml_engine.
# Tracks per-key event counts in a sliding window and returns a [0,1] factor.
# ──────────────────────────────────────────────────────────────────────────────

class FrequencyAnalyzer:
    """
    Sliding-window event counter.  Keys are typically IP addresses, hostnames,
    or (source, event_type) pairs.  Returns a frequency factor in [0, 1] and
    whether a burst threshold has been crossed.
    """

    def __init__(self, window_seconds: float = 300.0, burst_threshold: int = 20):
        self._window = window_seconds
        self._burst = burst_threshold
        self._history: defaultdict = defaultdict(lambda: deque(maxlen=1000))

    def record_and_score(self, key: str) -> tuple[float, bool]:
        """
        Record one event for `key` and return (frequency_factor, is_burst).
        frequency_factor: 0=normal, 1=extreme burst
        is_burst: True if count exceeds burst_threshold in the window
        """
        now = time.time()
        dq  = self._history[key]
        dq.append(now)
        # Prune old events
        while dq and now - dq[0] > self._window:
            dq.popleft()

        count = len(dq)
        factor = float(np.clip(count / self._burst, 0.0, 1.0))
        return factor, count >= self._burst


_freq_analyzer = FrequencyAnalyzer(window_seconds=300.0, burst_threshold=20)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_mongo_internal(log: dict) -> bool:
    source  = str(log.get("source", "")).upper()
    message = str(log.get("message", ""))
    if any(noise in source for noise in _MONGO_NOISE_SOURCES):
        return True
    if "'$date'" in message and "'c': 'NETWORK'" in message:
        return True
    return False


def _severity_index(sev: str) -> int:
    try:
        return _SEVERITY_ORDER.index(sev)
    except ValueError:
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# Confidence-Weighted Consensus Voter
# Instead of "highest wins", each candidate gets a weighted vote.
# ──────────────────────────────────────────────────────────────────────────────

def _consensus_vote(
    rule_sev: str,
    rule_conf: float,
    ml_sev: str,
    ml_score: float,
    sup_sev: str,
    sup_conf: float,
    freq_factor: float,
) -> tuple[str, str, float]:
    """
    Returns (final_severity, reason, composite_score).

    Voting logic:
      - Each layer casts a vote weighted by its confidence.
      - The weighted average severity index is computed.
      - An upward bias is applied proportional to the frequency factor.
    """
    votes: list[tuple[str, float, str]] = []  # (severity, weight, reason)

    if rule_sev != "information":
        votes.append((rule_sev, rule_conf * 1.2, f"Rule: {rule_sev}"))   # rules get 20% bonus

    if ml_sev != "information":
        votes.append((ml_sev, ml_score, f"ML anomaly ({ml_score:.2f})"))

    if sup_sev != "information" and sup_conf > 0.5:
        votes.append((sup_sev, sup_conf, f"Supervised: {sup_sev}"))

    if not votes:
        return "information", "No signals above information", 0.0

    # Compute weighted severity index
    total_w = sum(w for _, w, _ in votes)
    weighted_idx = sum(_severity_index(sev) * w for sev, w, _ in votes) / total_w

    # Frequency burst can push the score up (max +0.5 levels)
    weighted_idx += freq_factor * 0.5

    # Round to nearest integer severity level (conservative: floor)
    idx = int(np.floor(np.clip(weighted_idx, 0, len(_SEVERITY_ORDER) - 1)))

    # Build reason from highest-confidence vote
    best_vote = max(votes, key=lambda v: v[1])
    composite_score = float(np.clip(total_w / max(len(votes), 1), 0.0, 1.0))

    return _SEVERITY_ORDER[idx], best_vote[2], composite_score


# ──────────────────────────────────────────────────────────────────────────────
# Main classifier
# ──────────────────────────────────────────────────────────────────────────────

def classify(log: dict, ml_result: Any) -> tuple["SeverityResult", bool]:
    """
    Layered Consensus Engine v2.

    Layers:
      0. Noise filter (MongoDB internal / static safe patterns)
      1. Deterministic rules with confidence scores
      2. Supervised text ML
      3. Unsupervised structural ML + temporal boost
      4. Frequency burst analyzer
      5. Confidence-weighted consensus vote
      6. Insight generation
    """

    message    = str(log.get("message", "")) + " " + str(log.get("raw", ""))
    event_type = str(log.get("event_type", "") or "")
    source_key = str(log.get("source_ip", log.get("host", "default")))

    # ── 0. Noise filter ───────────────────────────────────────────────────────
    if _is_mongo_internal(log):
        return SeverityResult("information", "Internal noise (filtered)", "", 1.0, 0.0, 0.0), False

    is_safe = bool(_SAFE_PATTERNS.search(message))

    # ── 1. Deterministic rules ────────────────────────────────────────────────
    rule_severity = "information"
    rule_reason   = "No matching rules"
    rule_conf     = 0.0

    for pattern, sev, reason, conf in _RULES:
        if pattern.search(message) or pattern.search(event_type):
            if _severity_index(sev) > _severity_index(rule_severity):
                rule_severity = sev
                rule_reason   = reason
                rule_conf     = conf

    # ── 2. Supervised ML layer ────────────────────────────────────────────────
    sup_sev  = ml_result.supervised_sev
    sup_conf = ml_result.supervised_conf

    # ── 3. Structural ML layer ────────────────────────────────────────────────
    score      = ml_result.score
    is_anomaly = ml_result.is_anomaly

    ml_severity = "information"
    ml_reason   = ""

    if sup_conf > 0.85:
        ml_severity = sup_sev
        ml_reason   = f"Supervised high-confidence {sup_sev} ({sup_conf:.2f})"
    elif is_anomaly and not is_safe:
        for threshold, sev in _ML_THRESHOLDS:
            if score >= threshold:
                ml_severity = sev
                ml_reason   = f"Anomaly {sev} (score={score:.2f})"
                break
        # Cross-check: if structural says disaster but text says safe, temper it
        if ml_severity == "disaster" and sup_sev == "information" and sup_conf > 0.60:
            ml_severity = "warning"
            ml_reason   = "Novel structural pattern (safe text context) → warning"

    # ── 4. Frequency burst analysis ───────────────────────────────────────────
    freq_factor, is_burst = _freq_analyzer.record_and_score(source_key)

    # If burst AND anomaly, force at least medium
    if is_burst and is_anomaly and _severity_index(ml_severity) < _severity_index("medium"):
        ml_severity = "medium"
        ml_reason   = f"Burst activity from {source_key} ({freq_factor:.2f})"

    # ── 5. Confidence-weighted consensus vote ─────────────────────────────────
    # Hard rules that should never be downgraded
    _HARD_DISASTERS = {"Container OOM killed", "Disk full", "Process crashed",
                       "Database crash/corruption", "Shell spawn / possible RCE",
                       "Dropper / pipe-to-shell pattern", "OOM killer fired"}

    if rule_severity == "disaster" and rule_reason in _HARD_DISASTERS:
        # Hard physical events — never downgrade
        final_severity = "disaster"
        final_reason   = rule_reason
        composite_score = rule_conf
    else:
        final_severity, final_reason, composite_score = _consensus_vote(
            rule_sev=rule_severity,
            rule_conf=rule_conf,
            ml_sev=ml_severity,
            ml_score=score,
            sup_sev=sup_sev,
            sup_conf=sup_conf,
            freq_factor=freq_factor,
        )

    # Safe patterns always dampen (but don't suppress hard physical disasters)
    if is_safe and rule_severity != "disaster":
        # Dampen: cap at warning
        if _severity_index(final_severity) > _severity_index("warning"):
            final_severity = "warning"
            final_reason   = "Dampened: safe-pattern context"

    # ── 6. Insight ────────────────────────────────────────────────────────────
    insight = _interpreter.interpret(message)

    # ── 7. Final anomaly flag ─────────────────────────────────────────────────
    final_is_anomaly = is_anomaly and final_severity != "information" and not is_safe

    return (
        SeverityResult(
            severity         = final_severity,
            reason           = final_reason,
            insight          = insight,
            rule_confidence  = round(rule_conf, 4),
            frequency_factor = round(freq_factor, 4),
            final_score      = round(composite_score, 4),
        ),
        final_is_anomaly,
    )