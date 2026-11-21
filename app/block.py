from __future__ import annotations

import contextvars
import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.types import (CallbackQuery, InlineQuery, Message, MessageReactionUpdated, PreCheckoutQuery,
                           TelegramObject, Update)

from app import db
from app.config import get_settings
from app.keyboards import blocked_keyboard
from app.notices import notice_text

logger = logging.getLogger("rm-shop.block")

def blocked_notice() -> str:
    return notice_text("blocked")
_COOLDOWN = 4.0
_notice: contextvars.ContextVar[bool] = contextvars.ContextVar("blocked_notice", default=False)
_last_sent_at: dict[int, float] = {}


async def notify_blocked(bot: Bot, chat_id: int) -> None:
    now = time.monotonic()
    if now - _last_sent_at.get(chat_id, 0.0) < _COOLDOWN:
        return
    token = _notice.set(True)   # the one message a sharing block may send (sharing_notify_user)
    try:
        await bot.send_message(chat_id, blocked_notice(), reply_markup=blocked_keyboard())
        _last_sent_at[chat_id] = now
    except Exception:
        logger.debug("Не удалось отправить уведомление о блоке chat=%s", chat_id, exc_info=True)
    finally:
        _notice.reset(token)


def _inner(event: TelegramObject) -> TelegramObject:
    if isinstance(event, Update):
        return event.event
    return event


class BlockedByAdmin(RuntimeError):
    """The bot does not write to a person blocked in the admin panel: no broadcasts, no notices, no replies."""


# Methods that only read or clean up are let through; everything else aimed at a blocked person's chat is dropped.
_PASS_PREFIXES = ("Get", "Delete", "Ban", "Unban")


class BlockedRequestMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        chat_id = getattr(method, "chat_id", None)
        if (isinstance(chat_id, int) and chat_id > 0 and not type(method).__name__.startswith(_PASS_PREFIXES)
                and not _notice.get() and chat_id not in get_settings().admin_id_set and await db.user_is_blocked(chat_id)):
            raise BlockedByAdmin(f"{type(method).__name__} to {chat_id}: blocked in the admin panel")
        return await make_request(bot, method)


class BlockedMiddleware(BaseMiddleware):
    """A blocked person gets nothing back from the bot: messages, buttons and reactions are dropped silently."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        inner = _inner(event)
        if not isinstance(inner, (Message, CallbackQuery, MessageReactionUpdated, InlineQuery, PreCheckoutQuery)):
            return await handler(event, data)
        user = getattr(inner, "from_user", None) or getattr(inner, "user", None)
        if not user:
            return await handler(event, data)
        if user.id in get_settings().admin_id_set:
            return await handler(event, data)
        if not await db.user_is_blocked(user.id):
            return await handler(event, data)
        return None
