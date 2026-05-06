"""
Shim for backward compatibility.
Points to the new SmartMLEngine.
"""

from services.smart_ml_engine import SmartMLEngine as MLEngine, get_smart_ml_engine as get_ml_engine

__all__ = ["MLEngine", "get_ml_engine"]
