"""People from Iran (Telegram is blocked there, they find the bot in search) cannot pay and the VPN does not work
for them, yet they start the bot, take the gift and create devices.

They are recognised by the Telegram interface language («fa») or by Persian letters in the name. Such a newcomer
gets one short reply in Persian and English and nothing else: no row in `users`, so no gift, no device and no
trace in any statistics. They are remembered in `region_rejects`; the admin can let a person through by hand.
People already in the base are found and removed from the admin (Настройки → «Пользователи из Ирана»).
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.region")

LANGUAGES = {"fa"}
# Letters of the Persian alphabet that Arabic does not use: پ چ ژ گ, and the Persian forms of kaf and ye (ک ی).
PERSIAN = re.compile("[پچژگکی]")
REPLY = ("متأسفیم، این سرویس در منطقه شما در دسترس نیست.\n"
         "Sorry, this service is not available in your region.")
CACHE_SECONDS = 600

_cache: dict[int, tuple[float, bool]] = {}   # telegram id → (when, let through)


def suspicious(language: str | None, *names: str | None) -> str:
    """Why this person looks like Iran: «язык fa», «имя», or "" when they do not."""
    lang = str(language or "").lower().split("-")[0]
    if lang in LANGUAGES:
        return f"язык {lang}"
    if any(PERSIAN.search(str(n or "")) for n in names):
        return "имя"
    return ""


async def _let_through(user) -> bool:
    uid = int(user.id)
    hit = _cache.get(uid)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    pool = db._pool_req()
    row = await pool.fetchrow("SELECT allowed_at FROM region_rejects WHERE telegram_id = $1", uid)
    if row is not None:
        ok = row["allowed_at"] is not None
    elif await pool.fetchval("SELECT 1 FROM users WHERE telegram_id = $1", uid):
        ok = True   # already in the base: the admin sorts them out by hand
    else:
        reason = suspicious(getattr(user, "language_code", None), user.first_name, user.last_name)
        if not reason:
            ok = True
        else:
            await pool.execute(
                """INSERT INTO region_rejects (telegram_id, language, first_name, last_name, username, reason)
                   VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (telegram_id) DO NOTHING""",
                uid, getattr(user, "language_code", None), user.first_name, user.last_name, user.username, reason)
            _cache[uid] = (time.monotonic(), False)
            return False
    _cache[uid] = (time.monotonic(), ok)
    return ok


def forget(telegram_id: int) -> None:
    _cache.pop(int(telegram_id), None)


async def allow_web_user(user) -> bool:
    """The cabinet opened from the menu button without /start: the same check on its Telegram user."""
    if user is None or not get_settings().region_filter_enabled or int(user.id) in get_settings().admin_id_set:
        return True
    try:
        return await _let_through(user)
    except Exception:
        logger.warning("Фильтр региона не сработал для кабинета %s", user.id, exc_info=True)
        return True


class RegionFilterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not get_settings().region_filter_enabled:
            return await handler(event, data)
        inner = event.event if isinstance(event, Update) else event
        user = getattr(inner, "from_user", None)
        if not user or user.is_bot or user.id in get_settings().admin_id_set:
            return await handler(event, data)
        chat = getattr(inner, "chat", None) or getattr(getattr(inner, "message", None), "chat", None)
        if chat is not None and getattr(chat, "type", "private") != "private":
            return await handler(event, data)   # channel and group events are not about using the bot
        try:
            if await _let_through(user):
                return await handler(event, data)
            hits = await db._pool_req().fetchval(
                "UPDATE region_rejects SET hits = hits + 1, last_at = NOW() WHERE telegram_id = $1 RETURNING hits",
                int(user.id))
        except Exception:
            logger.warning("Фильтр региона не сработал для %s", user.id, exc_info=True)
            return await handler(event, data)
        if int(hits or 0) == 1 and hasattr(inner, "answer") and getattr(inner, "text", None) is not None:
            try:
                await inner.answer(REPLY)   # once: after that the bot stays silent
            except Exception:
                logger.debug("Ответ о регионе не ушёл %s", user.id, exc_info=True)
        return None


CANDIDATES_SQL = f"""
SELECT users.telegram_id, users.first_name, users.username, users.created_at,
       (SELECT COUNT(*) FROM devices d WHERE d.telegram_id = users.telegram_id)::int AS device_count
FROM users
WHERE users.first_name ~ '[\u067e\u0686\u0698\u06af\u06a9\u06cc]'
  AND NOT {db._PAID_SQL}
  AND users.telegram_id <> ALL($1::bigint[])
ORDER BY users.created_at DESC
LIMIT 500
"""


async def overview() -> dict:
    """The admin's view: who is already in the base and looks Iranian (never paid), and who was turned away."""
    pool = db._pool_req()
    admins = sorted(get_settings().admin_id_set)
    cands = [dict(r) for r in await pool.fetch(CANDIDATES_SQL, admins)]
    rejects = await pool.fetchrow(
        """SELECT COUNT(*) FILTER (WHERE allowed_at IS NULL)::int AS rejected,
                  COUNT(*) FILTER (WHERE allowed_at IS NULL AND first_at > NOW() - INTERVAL '1 day')::int AS day,
                  COUNT(*) FILTER (WHERE allowed_at IS NOT NULL)::int AS allowed
           FROM region_rejects""")
    recent = [dict(r) for r in await pool.fetch(
        """SELECT telegram_id, first_name, username, language, reason, hits, first_at, allowed_at
           FROM region_rejects ORDER BY first_at DESC LIMIT 50""")]
    return {"enabled": get_settings().region_filter_enabled, "candidates": [db._jsonable(c) for c in cands],
            **dict(rejects), "recent": [db._jsonable(r) for r in recent]}


async def remember(telegram_id: int, first_name: str | None, username: str | None, reason: str) -> None:
    await db._pool_req().execute(
        """INSERT INTO region_rejects (telegram_id, first_name, username, reason) VALUES ($1, $2, $3, $4)
           ON CONFLICT (telegram_id) DO UPDATE SET allowed_at = NULL, reason = EXCLUDED.reason""",
        int(telegram_id), first_name, username, reason)
    forget(telegram_id)


async def allow(telegram_id: int) -> bool:
    done = await db._pool_req().fetchval(
        "UPDATE region_rejects SET allowed_at = NOW() WHERE telegram_id = $1 RETURNING 1", int(telegram_id))
    forget(telegram_id)
    return bool(done)
