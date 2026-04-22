"""Abstract base parser."""
from abc import ABC, abstractmethod
from typing import Optional


class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw: str) -> Optional[dict]:
        """Parse a raw log line into a structured dict. Return None on failure."""
