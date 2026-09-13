from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import web

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.office")

MESSAGE_MAX = 160
VALID_STATES = frozenset({"busy", "idle", "offline"})
STATE_ALIASES = {
    "active": "busy",
    "working": "busy",
    "work": "busy",
    "online": "idle",
    "away": "idle",
    "stale": "offline",
    "off": "offline",
}


@dataclass(frozen=True)
class AgentDef:
    id: str
    name: str
    role: str
    aliases: tuple[str, ...] = ()


ROSTER: tuple[AgentDef, ...] = (
    AgentDef("monday", "Понедельник", "код / фичи", ("ponedelnik", "понедельник")),
    AgentDef("friday", "Пятница", "Threads / PR", ("pyatnica", "пятница")),
    AgentDef("thursday", "Четверг", "метрики", ("chetverg", "четверг")),
    AgentDef("product", "Продакт", "QA / деплой", ("prodakt", "продакт", "qa")),
)

_ALIAS_TO_ID: dict[str, str] = {}
for _agent in ROSTER:
    _ALIAS_TO_ID[_agent.id] = _agent.id
    _ALIAS_TO_ID[_agent.name.casefold()] = _agent.id
    for _alias in _agent.aliases:
        _ALIAS_TO_ID[_alias.casefold()] = _agent.id


def roster_public() -> list[dict[str, str]]:
    return [{"id": a.id, "name": a.name, "role": a.role} for a in ROSTER]


def resolve_agent_id(raw: Any) -> str | None:
    key = str(raw or "").strip().casefold()
    if not key:
        return None
    return _ALIAS_TO_ID.get(key)


def normalize_state(raw: Any) -> str | None:
    key = str(raw or "").strip().casefold()
    if not key:
        return None
    key = STATE_ALIASES.get(key, key)
    if key in VALID_STATES:
        return key
    return None


def clip_message(raw: Any) -> str:
    text = " ".join(str(raw or "").split())
    if len(text) > MESSAGE_MAX:
        return text[:MESSAGE_MAX].rstrip()
    return text


def parse_source_ts(raw: Any) -> datetime | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(raw).strip()
    if not text:
        return None
    if text.replace(".", "", 1).isdigit():
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def stale_cutoff(minutes: int, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now - timedelta(minutes=max(1, int(minutes)))


def effective_state(row: dict | None, minutes: int, now: datetime | None = None) -> tuple[str, bool]:
    if not row:
        return "offline", True
    updated = parse_source_ts(row.get("updated_at"))
    if updated is None or updated < stale_cutoff(minutes, now):
        return "offline", True
    reported = normalize_state(row.get("state")) or "idle"
    return reported, False


def _dt_iso(value: Any) -> str | None:
    dt = parse_source_ts(value)
    return dt.isoformat() if dt else None


def build_office_payload(rows: list[dict], minutes: int, now: datetime | None = None) -> dict:
    by_id = {str(r.get("agent_id") or ""): r for r in rows}
    agents = []
    for agent in ROSTER:
        row = by_id.get(agent.id)
        state, stale = effective_state(row, minutes, now)
        agents.append(
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "state": state,
                "reported_state": (normalize_state((row or {}).get("state")) if row else None),
                "message": str((row or {}).get("message") or ""),
                "updated_at": _dt_iso((row or {}).get("updated_at")),
                "source_ts": _dt_iso((row or {}).get("source_ts")),
                "stale": stale,
            }
        )
    return {
        "ok": True,
        "stale_minutes": max(1, int(minutes)),
        "agents": agents,
    }


def _extract_write_token(request: web.Request) -> str:
    header = (request.headers.get("X-Office-Token") or "").strip()
    if header:
        return header
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _write_token_ok(given: str) -> bool:
    expected = (get_settings().office_status_token or "").strip()
    if not expected or not given:
        return False
    left = given.encode("utf-8")
    right = expected.encode("utf-8")
    if len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


async def api_office_status_write(request: web.Request) -> web.Response:
    settings = get_settings()
    if not (settings.office_status_token or "").strip():
        return web.json_response(
            {"ok": False, "error": "Задайте OFFICE_STATUS_TOKEN в .env"},
            status=503,
        )
    if not _write_token_ok(_extract_write_token(request)):
        return web.json_response({"ok": False, "error": "Неверный токен"}, status=403)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    agent_id = resolve_agent_id(body.get("agent_id") or body.get("id") or body.get("agent"))
    if not agent_id:
        return web.json_response(
            {
                "ok": False,
                "error": "Неизвестный агент",
                "agents": [a.id for a in ROSTER],
            },
            status=400,
        )
    state = normalize_state(body.get("state") or body.get("status"))
    if not state:
        return web.json_response(
            {
                "ok": False,
                "error": "Нужен state: busy, idle или offline",
            },
            status=400,
        )
    message = clip_message(body.get("message") or body.get("text") or body.get("doing") or body.get("note"))
    source_ts = parse_source_ts(body.get("ts") or body.get("timestamp") or body.get("updated_at"))
    row = await db.upsert_office_status(agent_id, state, message, source_ts)
    minutes = int(settings.office_stale_minutes or 8)
    effective, stale = effective_state(row, minutes)
    return web.json_response(
        {
            "ok": True,
            "agent_id": agent_id,
            "state": effective,
            "reported_state": state,
            "message": message,
            "updated_at": _dt_iso((row or {}).get("updated_at")),
            "stale": stale,
        }
    )


async def api_office_status_read(request: web.Request) -> web.Response:
    from app.admin import _need_auth

    denied = _need_auth(request)
    if denied:
        return denied
    settings = get_settings()
    minutes = int(settings.office_stale_minutes or 8)
    rows = await db.list_office_status()
    return web.json_response(build_office_payload(rows, minutes))


def mount_office(app: web.Application) -> None:
    app.router.add_post("/api/office/status", api_office_status_write)
    app.router.add_get("/admin/api/office", api_office_status_read)
