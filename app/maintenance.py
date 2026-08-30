from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app import db
from app.config import get_settings
from app.trust import MAINTENANCE_TEXT


async def current_text() -> str:
    stored = (await db.get_kv("maintenance_notice")).strip()
    return stored or MAINTENANCE_TEXT


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        text = getattr(event, "text", None) or ""
        if user and user.id in get_settings().admin_id_set:
            return await handler(event, data)
        if isinstance(event, Message) and text.startswith("/admin"):
            return await handler(event, data)
        if not await db.flag_on("maintenance"):
            return await handler(event, data)
        notice = await current_text()
        if isinstance(event, CallbackQuery):
            try:
                await event.answer(notice[:200], show_alert=True)
            except Exception:
                pass
            return None
        if isinstance(event, Message):
            try:
                await event.answer(notice)
            except Exception:
                pass
            return None
        return None
