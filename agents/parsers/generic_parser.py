import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from parsers.base_parser import BaseParser

# Aggressive timestamp patterns for removal from messages
_TS_PATTERNS = [
    # YYYY-MM-DD HH:MM:SS or ISO
    re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s*"),
    # Syslog: Apr 23 10:22:01
    re.compile(r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s*"),
    # Simple time: 10:22:01
    re.compile(r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?\s*"),
    # Bracketed: [2026-05-08 06:58:51]
    re.compile(r"^\[\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*"),
]

def strip_timestamps(text: str) -> str:
    """Repeatedly strip timestamp-like prefixes from the start of a string."""
    current = text.strip()
    changed = True
    while changed:
        changed = False
        for pattern in _TS_PATTERNS:
            match = pattern.match(current)
            if match:
                current = current[match.end():].strip()
                changed = True
                break
    return current

class GenericParser(BaseParser):
    def parse(self, raw: str) -> Optional[dict]:
        # Kathmandu is UTC +5:45
        tz_kathmandu = timezone(timedelta(hours=5, minutes=45))
        now = datetime.now(tz_kathmandu)
        
        # Try to extract a timestamp for the event field, but strip it from message
        ts_iso = now.isoformat()
        for pattern in _TS_PATTERNS:
            match = pattern.match(raw)
            if match:
                # If we found a timestamp, we don't necessarily try to parse it for the DB 
                # (to avoid complex date parsing), but we definitely strip it.
                break
        
        clean_msg = strip_timestamps(raw)

        return {
            "timestamp": ts_iso,
            "source": "generic",
            "event_type": "generic_log",
            "message": clean_msg or raw,
        }
