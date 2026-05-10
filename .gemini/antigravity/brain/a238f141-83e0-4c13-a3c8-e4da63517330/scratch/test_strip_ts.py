import re

_TS_PATTERNS = [
    # ISO 8601 & Common: 2024-05-10 14:30:00, 2024/05/10 14:30:00, with optional T, Z, or brackets
    r"\[?\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\]?",
    # Nginx/Apache: [10/May/2024:14:30:00 +0000]
    r"\[?\d{1,2}/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/\d{4}:\d{2}:\d{2}:\d{2}(?:\s[+-]\d{4})?\]?",
    # Syslog: May 10 14:30:00
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}",
    # Time only: 14:30:00 or 14:30:00.123
    r"\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b",
    # Date only: 2024-05-10
    r"\b\d{4}[-/]\d{2}[-/]\d{2}\b",
]

_TS_RE = re.compile("|".join(_TS_PATTERNS), re.I)

def strip_timestamps(msg: str) -> str:
    # Remove the timestamps
    cleaned = _TS_RE.sub("", msg)
    # Clean up double spaces and leading/trailing whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Remove leading colons or dashes often left after timestamp
    cleaned = re.sub(r"^[ :-]+", "", cleaned)
    return cleaned

test_logs = [
    "2026-05-10 14:37:13 Connection accepted from 192.168.1.1",
    "May 10 14:37:13 sshd[1234]: Accepted password for root",
    "[10/May/2026:14:37:13 +0000] GET /index.html 200",
    "14:37:13.456 ERROR: Database connection failed",
    "Log at 2026-05-10: System rebooted",
    "Some message without timestamp",
    "[2026-05-10 14:37:13] [INFO] Starting service...",
]

for log in test_logs:
    print(f"Original: {log}")
    print(f"Cleaned:  {strip_timestamps(log)}")
    print("-" * 20)
