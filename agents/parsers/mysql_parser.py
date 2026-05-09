"""
MySQL error log parser.

Example:
  2024-04-15T10:22:01.123456Z 0 [ERROR] [MY-000000] [Server] /usr/sbin/mysqld: Table './db/tbl' is marked as crashed
  2024-04-15T10:22:01.123456Z 1 [Warning] [MY-011061] [Server] Ignoring --secure-file-priv value
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from parsers.base_parser import BaseParser

_MYSQL_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}T[\d:.]+Z)\s+"
    r"(?P<thread>\d+)\s+"
    r"\[(?P<level>[^\]]+)\]"
    r"(?:\s+\[[^\]]+\])?"      # optional [MY-######]
    r"(?:\s+\[[^\]]+\])?"      # optional [Server]
    r"\s+(?P<message>.+)"
)

_LEGACY_RE = re.compile(
    r"(?P<ts>\d{6}\s+\d{1,2}:\d{2}:\d{2})\s+(?P<message>.+)"
)


class MySQLParser(BaseParser):
    def parse(self, raw: str) -> Optional[dict]:
        m = _MYSQL_RE.match(raw)
        if m:
            return {
                "timestamp": m.group("ts").replace("Z", "+00:00"),
                "source": "mysql",
                "event_type": "db_error" if "error" in m.group("level").lower() else "db_log",
                "level": m.group("level"),
                "message": m.group("message").strip(),
            }
        m2 = _LEGACY_RE.match(raw)
        if m2:
            # Kathmandu is UTC +5:45
            tz_kathmandu = timezone(timedelta(hours=5, minutes=45))
            return {
                "timestamp": datetime.now(tz_kathmandu).isoformat(),
                "source": "mysql",
                "event_type": "db_log",
                "message": m2.group("message").strip(),
            }
        return None
