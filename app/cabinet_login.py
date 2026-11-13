"""Browser login to the cabinet: what the bot says about a login and which device it came from."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from app.notices import notice_text

MSK = timezone(timedelta(hours=3))
START_PREFIX = "lk_"
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,40}$")

_BROWSERS = (
    ("YaBrowser", "Яндекс Браузер"),
    ("Edg", "Edge"),
    ("OPR", "Opera"),
    ("SamsungBrowser", "Samsung Internet"),
    ("FxiOS", "Firefox"),
    ("Firefox", "Firefox"),
    ("CriOS", "Chrome"),
    ("Chrome", "Chrome"),
    ("Safari", "Safari"),
)
_SYSTEMS = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("Windows", "Windows"),
    ("CrOS", "Chromebook"),
    ("Macintosh", "Mac"),
    ("Linux", "Linux"),
)


def device_label(user_agent: str | None) -> str:
    """«Chrome на Windows» from a User-Agent. Only fixed words come out, nothing from the header itself."""
    ua = user_agent or ""
    browser = next((name for key, name in _BROWSERS if key in ua), "Браузер")
    system = next((name for key, name in _SYSTEMS if key in ua), "")
    return f"{browser} на {system}" if system else browser


def start_challenge_id(payload: str | None) -> str:
    """The login id from /start lk_<id>, or "" if the payload is something else."""
    raw = (payload or "").strip()
    if not raw.startswith(START_PREFIX):
        return ""
    cid = raw[len(START_PREFIX):]
    return cid if _ID_RE.match(cid) else ""


def _when(at: datetime | None) -> str:
    moment = (at or datetime.now(timezone.utc)).astimezone(MSK)
    return f"сегодня, {moment:%H:%M} МСК" if moment.date() == datetime.now(MSK).date() else f"{moment:%d.%m, %H:%M} МСК"


def request_text(device: str | None, at: datetime | None = None) -> str:
    return notice_text("cabinet_login", device=device or "Браузер", time=_when(at))


def approved_text(device: str | None) -> str:
    return notice_text("cabinet_login_ok", device=device or "браузер")
