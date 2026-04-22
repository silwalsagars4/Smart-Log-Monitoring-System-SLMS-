"""
Alert dispatch service — sends notifications via Email (SMTP) and Telegram.
Called by the pipeline consumer when severity is High or Disaster.
"""

import logging
from datetime import datetime, timezone

import httpx
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_alert(log: dict, severity: str, reason: str):
    """Dispatch alert notification for high/disaster severity logs."""
    if severity not in ("high", "disaster"):
        return
    if settings.ENABLE_EMAIL:
        await _send_email(log, severity, reason)
    if settings.ENABLE_TELEGRAM:
        await _send_telegram(log, severity, reason)


def _build_message(log: dict, severity: str, reason: str) -> str:
    ts = log.get("timestamp", datetime.now(timezone.utc).isoformat())
    source = log.get("source", "unknown")
    ip = log.get("ip", "N/A")
    msg = log.get("message", "")
    return (
        f"🚨 SLMS ALERT [{severity.upper()}]\n"
        f"Time: {ts}\n"
        f"Source: {source}\n"
        f"IP: {ip}\n"
        f"Reason: {reason}\n"
        f"Message: {msg[:300]}"
    )


async def _send_email(log: dict, severity: str, reason: str):
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        body = _build_message(log, severity, reason)
        msg = MIMEText(body)
        msg["Subject"] = f"[SLMS] {severity.upper()} Alert — {log.get('source', 'unknown')}"
        msg["From"] = settings.ALERT_FROM
        msg["To"] = settings.ALERT_TO
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("Email alert sent: %s", msg["Subject"])
    except Exception as exc:
        logger.error("Email alert failed: %s", exc)


async def _send_telegram(log: dict, severity: str, reason: str):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    try:
        body = _build_message(log, severity, reason)
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": body})
            resp.raise_for_status()
        logger.info("Telegram alert sent.")
    except Exception as exc:
        logger.error("Telegram alert failed: %s", exc)
