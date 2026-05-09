"""
SSH / auth.log parser.

Source tagging:
  - sshd daemon events  → source = "ssh"
  - sudo / PAM events   → source = "auth"

Example lines:
  Apr 15 10:22:01 host sshd[12345]: Failed password for root from 192.168.1.1 port 22 ssh2
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from parsers.base_parser import BaseParser

_SSHD_RE = re.compile(
    r"(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\S+)\s+\S+\s+sshd\[\d+\]:\s+"
    r"(?P<event>Failed|Accepted|Invalid|Disconnected|Connection closed|error:).*?"
    r"(?:\s+for\s+(?P<user>\S+))?"
    r"(?:\s+from\s+(?P<ip>\d{1,3}(?:\.\d{1,3}){3}))?"
    r"(?:\s+port\s+(?P<port>\d+))?",
    re.IGNORECASE,
)

_SUDO_RE = re.compile(
    r"(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\S+)\s+\S+\s+sudo.*?USER=(?P<sudo_user>\S+)\s*;.*?COMMAND=(?P<command>.+)"
)

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
)}

def _build_ts(month: str, day: str, time_str: str) -> str:
    tz_kathmandu = timezone(timedelta(hours=5, minutes=45))
    now = datetime.now(tz_kathmandu)
    month_num = _MONTHS.get(month[:3].capitalize(), now.month)
    year = now.year
    try:
        dt = datetime(year, month_num, int(day), *[int(x) for x in time_str.split(":")])
        return dt.replace(tzinfo=tz_kathmandu).isoformat()
    except Exception:
        return now.isoformat()

class SSHParser(BaseParser):
    def parse(self, raw: str) -> Optional[dict]:
        m = _SSHD_RE.match(raw)
        if m:
            event = m.group("event").lower()
            is_failure = "failed" in event or "invalid" in event
            msg = raw.split("]:", 1)[-1].strip() if "]:" in raw else raw
            return {
                "timestamp": _build_ts(m.group("month"), m.group("day"), m.group("time")),
                "source": "ssh",
                "event_type": "auth_failure" if is_failure else "auth_success",
                "user": m.group("user") or "",
                "ip": m.group("ip") or "",
                "port": m.group("port") or "",
                "message": msg,
            }

        m2 = _SUDO_RE.match(raw)
        if m2:
            msg = f"sudo: USER={m2.group('sudo_user')} ; COMMAND={m2.group('command')}"
            return {
                "timestamp": _build_ts(m2.group("month"), m2.group("day"), m2.group("time")),
                "source": "auth",
                "event_type": "sudo",
                "user": m2.group("sudo_user") or "",
                "ip": "",
                "command": m2.group("command").strip(),
                "message": msg,
            }
        return None
