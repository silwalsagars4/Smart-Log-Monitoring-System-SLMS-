import re
from parsers.base_parser import BaseParser
from typing import Optional
from datetime import datetime, timezone, timedelta

# Common Docker/Container timestamp patterns at the start of the line
_TS_PATTERNS = [
    re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s*"),
    re.compile(r"^\[\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*"),
    re.compile(r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?\s*"),
]

def strip_timestamps(text: str) -> str:
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

class DockerParser(BaseParser):
    def parse(self, raw: str) -> Optional[dict]:
        # Kathmandu is UTC +5:45
        tz_kathmandu = timezone(timedelta(hours=5, minutes=45))
        
        clean_msg = strip_timestamps(raw)

        return {
            "timestamp": datetime.now(tz_kathmandu).isoformat(),
            "source": "docker",
            "event_type": "container_log",
            "message": clean_msg or raw,
        }
