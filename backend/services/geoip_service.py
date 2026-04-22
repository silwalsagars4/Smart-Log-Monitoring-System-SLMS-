"""
GeoIP service — resolves IP addresses to geographic location using MaxMind GeoLite2.
Degrades gracefully if database is not available.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)
_reader = None


def _init_reader():
    global _reader
    if _reader is not None:
        return
    db_path = os.environ.get("GEOIP_DB_PATH", "/app/geoip/GeoLite2-City.mmdb")
    if not os.path.exists(db_path):
        logger.info("GeoIP database not found at %s — GeoIP disabled.", db_path)
        return
    try:
        import geoip2.database
        _reader = geoip2.database.Reader(db_path)
        logger.info("GeoIP reader initialised from %s", db_path)
    except Exception as exc:
        logger.warning("Failed to initialise GeoIP reader: %s", exc)


def lookup(ip: str) -> Optional[dict]:
    """Returns dict with country, city, lat, lon or None."""
    _init_reader()
    if _reader is None or not ip:
        return None
    try:
        response = _reader.city(ip)
        return {
            "country": response.country.name or "",
            "country_code": response.country.iso_code or "",
            "city": response.city.name or "",
            "lat": response.location.latitude,
            "lon": response.location.longitude,
        }
    except Exception:
        return None
