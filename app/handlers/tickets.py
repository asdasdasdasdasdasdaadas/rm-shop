from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.tickets import attachments_from_message, receive_user_message

router = Router()


@router.callback_query(F.data == "support_ticket")
async def support_hint(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Напишите сюда, что случилось. Можно прислать скриншот. Откроется тикет, ответ придёт в этот чат и в кабинет."
    )


@router.message(F.chat.type == "private")
async def ticket_from_chat(message: Message) -> None:
    if not message.from_user or message.from_user.is_bot:
        return
    text = (message.text or message.caption or "").strip()
    if text.startswith("/"):
        return
    files: list[dict] = []
    try:
        if message.photo or message.video or message.document or message.animation:
            files = await attachments_from_message(message.bot, message)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    except Exception:
        if not text:
            await message.answer("Не удалось принять файл. Пришлите фото, PDF или ZIP.")
            return
    if not text and not files:
        return
    try:
        await receive_user_message(
            message.bot,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            body=text,
            source="bot",
            attachments=files,
        )
    except ValueError:
        return
