from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.tickets import receive_user_message

router = Router()


@router.callback_query(F.data == "support_ticket")
async def support_hint(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Напишите сюда, что случилось. Откроется тикет, ответ придёт в этот чат и в кабинет."
    )


@router.message(F.text | F.caption)
async def ticket_from_chat(message: Message) -> None:
    if not message.from_user or message.from_user.is_bot:
        return
    if message.chat and message.chat.type != "private":
        return
    text = (message.text or message.caption or "").strip()
    if not text or text.startswith("/"):
        return
    try:
        await receive_user_message(
            message.bot,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            body=text,
            source="bot",
        )
    except ValueError:
        return
