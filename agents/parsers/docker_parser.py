"""Docker log lines don't have a universal format — pass through as-is."""

from parsers.base_parser import BaseParser
from typing import Optional
from datetime import datetime, timezone


class DockerParser(BaseParser):
    def parse(self, raw: str) -> Optional[dict]:
        # Timestamp already stripped by collector; return generic entry
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "docker",
            "event_type": "container_log",
            "message": raw,
        }
