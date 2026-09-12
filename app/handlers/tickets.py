from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app import db
from app.keyboards import help_connect_reply_keyboard
from app.notices import notice_text
from app.tickets import attachments_from_message, receive_user_message

router = Router()


@router.callback_query(F.data == "support_ticket")
async def support_hint(callback: CallbackQuery) -> None:
    await callback.answer()
    await _open_help_ticket(
        callback,
        "Обращение в поддержку.",
    )


@router.callback_query(F.data == "help:connect")
async def help_connect(callback: CallbackQuery) -> None:
    await callback.answer()
    n = 0
    if callback.from_user:
        n = await db.device_count(callback.from_user.id)
    key = "help_connect_has_device" if n else "help_connect_no_device"
    await callback.message.answer(
        notice_text(key),
        reply_markup=help_connect_reply_keyboard(),
    )


@router.callback_query(F.data == "help:other")
async def help_other(callback: CallbackQuery) -> None:
    await callback.answer()
    await _open_help_ticket(
        callback,
        "Другая проблема. Человек ещё не подключился.",
    )


async def _open_help_ticket(callback: CallbackQuery, body: str) -> None:
    user = callback.from_user
    if not user:
        return
    try:
        await receive_user_message(
            callback.bot,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            body=body,
            source="bot",
            ack_user=False,
        )
    except ValueError:
        await callback.message.answer(notice_text("help_other"))
        return
    await callback.message.answer(notice_text("help_other"))


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
