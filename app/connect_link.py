"""Link to the connect page: one device, no login, the key never in a query string.

The token rides in the URL fragment (`/connect#t=…`), so it never reaches server
logs or a Referer; the page sends it back in the `X-Connect-Token` header.
It is signed with a key derived from the bot token and carries the owner, the
device and an expiry — no table, and it opens only that device's key.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from app.config import get_settings

TTL_DAYS = 30
_SALT = b"frog-connect-v1"


def _key() -> bytes:
    return hmac.new(_SALT, get_settings().bot_token.encode(), hashlib.sha256).digest()


def _sign(body: str) -> str:
    mac = hmac.new(_key(), body.encode(), hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")


def make_token(telegram_id: int, device_id: int, *, days: int = TTL_DAYS, now: float | None = None) -> str:
    expires = int((now if now is not None else time.time()) + days * 86400)
    body = f"{int(telegram_id):x}.{int(device_id):x}.{expires:x}"
    return f"{body}.{_sign(body)}"


def read_token(token: str, *, now: float | None = None) -> tuple[int, int] | None:
    """(telegram_id, device_id) for a valid, unexpired token; None otherwise."""
    token = str(token or "").strip()
    if not token or len(token) > 120:
        return None
    parts = token.split(".")
    if len(parts) != 4:
        return None
    body = ".".join(parts[:3])
    if not hmac.compare_digest(_sign(body), parts[3]):
        return None
    try:
        telegram_id, device_id, expires = (int(x, 16) for x in parts[:3])
    except ValueError:
        return None
    if expires < (now if now is not None else time.time()):
        return None
    return telegram_id, device_id


def connect_url(base: str, telegram_id: int, device_id: int, app: str = "") -> str:
    base = str(base or "").rstrip("/")
    if not base:
        return ""
    url = f"{base}/connect#t={make_token(telegram_id, device_id)}"
    if app:
        url += f"&a={app}"
    return url
