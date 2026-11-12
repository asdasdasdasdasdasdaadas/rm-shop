from __future__ import annotations

import time

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.config import get_settings

ACTIVE_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.RESTRICTED,
}

_CACHE_TTL = 45.0
_cache: dict[int, tuple[float, bool]] = {}


async def is_channel_member(bot: Bot, user_id: int, *, force: bool = False) -> bool:
    settings = get_settings()
    if not settings.required_channel_enabled:
        return True
    now = time.monotonic()
    if not force:
        hit = _cache.get(user_id)
        if hit and hit[0] > now:
            return hit[1]
    try:
        member = await bot.get_chat_member(settings.required_channel_id, user_id)
        ok = member.status in ACTIVE_STATUSES
    except (TelegramBadRequest, TelegramForbiddenError):
        ok = False
    _cache[user_id] = (now + _CACHE_TTL, ok)
    return ok


async def is_customer(user_id: int) -> bool:
    """Has paid or has a device: the channel is only asked of newcomers, never of someone who already uses the service."""
    from app import db
    local = await db.get_user(user_id)
    if local and local.get("has_paid_topup"):
        return True
    return await db.device_count(user_id) > 0


async def channel_gate_passed(bot: Bot, user_id: int, *, force: bool = False) -> bool:
    """The channel check for bot menus and buttons: customers pass even after leaving the channel."""
    if not get_settings().required_channel_enabled:
        return True
    if await is_customer(user_id):
        return True
    return await is_channel_member(bot, user_id, force=force)
