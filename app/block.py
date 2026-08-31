from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, MessageReactionUpdated, TelegramObject, Update

from app import db
from app.config import get_settings
from app.keyboards import blocked_keyboard
from app.notices import notice_text

logger = logging.getLogger("rm-shop.block")

def blocked_notice() -> str:
    return notice_text("blocked")
_COOLDOWN = 4.0
_last_sent_at: dict[int, float] = {}


async def notify_blocked(bot: Bot, chat_id: int) -> None:
    now = time.monotonic()
    if now - _last_sent_at.get(chat_id, 0.0) < _COOLDOWN:
        return
    try:
        await bot.send_message(chat_id, blocked_notice(), reply_markup=blocked_keyboard())
        _last_sent_at[chat_id] = now
    except Exception:
        logger.debug("Не удалось отправить уведомление о блоке chat=%s", chat_id, exc_info=True)


def _inner(event: TelegramObject) -> TelegramObject:
    if isinstance(event, Update):
        return event.event
    return event


class BlockedMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        inner = _inner(event)
        if not isinstance(inner, (Message, CallbackQuery, MessageReactionUpdated)):
            return await handler(event, data)
        user = getattr(inner, "from_user", None)
        if not user:
            return await handler(event, data)
        if user.id in get_settings().admin_id_set:
            return await handler(event, data)
        if not await db.user_is_blocked(user.id):
            return await handler(event, data)
        bot: Bot | None = data.get("bot")
        if isinstance(inner, CallbackQuery):
            try:
                await inner.answer("Доступ ограничен", show_alert=True)
            except Exception:
                logger.debug("Не удалось ответить на callback при блоке", exc_info=True)
            chat = getattr(inner.message, "chat", None) if inner.message else None
            chat_id = chat.id if chat is not None else user.id
        elif isinstance(inner, Message):
            chat_id = inner.chat.id
        else:
            chat_id = user.id
        if bot and chat_id:
            await notify_blocked(bot, chat_id)
        return None
