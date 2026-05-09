"""
Nginx combined access log parser.

Format: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
Example:
  192.168.1.1 - - [15/Apr/2024:10:22:01 +0000] "GET /api/v1/health HTTP/1.1" 200 134 "-" "curl/7.68.0"
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from parsers.base_parser import BaseParser

_NGINX_RE = re.compile(
    r'(?P<ip>\S+)\s+-\s+(?P<user>\S+)\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\d+)\s+"(?P<referer>[^"]*)"\s+"(?P<agent>[^"]*)"'
)

_TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"


class NginxParser(BaseParser):
    def parse(self, raw: str) -> Optional[dict]:
        m = _NGINX_RE.match(raw)
        if not m:
            return None
        try:
            ts = datetime.strptime(m.group("time"), _TIME_FMT).isoformat()
        except ValueError:
            # Kathmandu is UTC +5:45
            tz_kathmandu = timezone(timedelta(hours=5, minutes=45))
            ts = datetime.now(tz_kathmandu).isoformat()

        status = int(m.group("status"))
        return {
            "timestamp": ts,
            "source": "nginx",
            "ip": m.group("ip"),
            "user": m.group("user") if m.group("user") != "-" else "",
            "method": m.group("method"),
            "path": m.group("path"),
            "status": status,
            "bytes": int(m.group("bytes")),
            "user_agent": m.group("agent"),
            "event_type": "http_error" if status >= 400 else "http_request",
            "message": f'{m.group("method")} {m.group("path")} → {status}',
        }
