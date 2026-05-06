"""
Generic passthrough parser.
Used for custom log paths added via the Dynamic Log Config feature.
Attempts to extract a timestamp; falls back to now(). Returns the full line as message.
"""

import re
from datetime import datetime, timezone
from typing import Optional

from parsers.base_parser import BaseParser

# ISO-8601 or syslog-style timestamps
_TS_ISO = re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)")
_TS_SYSLOG = re.compile(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})")


class GenericParser(BaseParser):
    def parse(self, raw: str) -> Optional[dict]:
        ts = datetime.now(timezone.utc).isoformat()
        m = _TS_ISO.search(raw)
        if m:
            try:
                ts = datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).isoformat()
            except ValueError:
                pass
        return {
            "timestamp": ts,
            "event_type": "generic_log",
            "message": raw,
        }
