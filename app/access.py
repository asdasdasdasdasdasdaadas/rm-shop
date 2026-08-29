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
    now = time.monotonic()
    if not force:
        hit = _cache.get(user_id)
        if hit and hit[0] > now:
            return hit[1]
    settings = get_settings()
    try:
        member = await bot.get_chat_member(settings.required_channel_id, user_id)
        ok = member.status in ACTIVE_STATUSES
    except (TelegramBadRequest, TelegramForbiddenError):
        ok = False
    _cache[user_id] = (now + _CACHE_TTL, ok)
    return ok
