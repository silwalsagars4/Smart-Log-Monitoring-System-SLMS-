"""
Fallback source detector.
Used when a parser returns None and the collector metadata is unavailable.
Inspects raw log content with regex patterns to infer the source.
"""

import re
from typing import Optional

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"sshd\[|Failed password|Accepted \w+ for|Invalid user|Disconnected from", re.I), "ssh"),
    (re.compile(r"sudo:|su\[|pam_unix|PAM authentication|auth\.log", re.I), "auth"),
    (re.compile(r"nginx|HTTP/\d\.\d.*\d{3}|\"(GET|POST|PUT|DELETE|PATCH|HEAD)", re.I), "nginx"),
    (re.compile(r"apache|httpd|mod_", re.I), "apache"),
    (re.compile(r"mysqld|InnoDB|Aborted connection|Got an error reading|MySQL.*\[Error\]", re.I), "mysql"),
    (re.compile(r"docker|containerd|container.*exited|OOMKilled", re.I), "docker"),
    (re.compile(r"kernel:|systemd\[|journald|ufw|iptables|NetworkManager", re.I), "system"),
]

_DEFAULT_SOURCE = "unknown"


def detect_source(raw: str) -> str:
    """Return the most likely log source for a raw log line."""
    for pattern, source in _PATTERNS:
        if pattern.search(raw):
            return source
    return _DEFAULT_SOURCE
