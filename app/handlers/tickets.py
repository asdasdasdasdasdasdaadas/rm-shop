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


@router.callback_query(F.data == "help:feedback")
async def help_feedback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Спасибо! Напишите здесь, что стоит улучшить или с какой проблемой вы столкнулись. "
        "Можно приложить скриншот — ваше сообщение получит поддержка.")


@router.callback_query(F.data == "help:other")
async def help_other(callback: CallbackQuery) -> None:
    await callback.answer()
    await _open_help_ticket(
        callback,
        "Другая проблема. Человек ещё не подключился.",
    )


async def _open_help_ticket(callback: CallbackQuery, body: str) -> None:
    # Viewing help is not a support request: the message handler opens
    # the ticket only when the user sends actual text or an attachment.
    await callback.message.answer(notice_text("help_other"))


@router.callback_query(F.data.startswith("ticket_close:"))
async def user_close_prompt(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    try:
        ticket_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректное обращение", show_alert=True)
        return
    ticket = await db.get_ticket(ticket_id)
    if not ticket or int(ticket["telegram_id"]) != callback.from_user.id:
        await callback.answer("Обращение не найдено", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer("Закрыть обращение? Новое сообщение откроет следующее.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Да, закрыть", callback_data=f"ticket_finish:{ticket_id}"),
        InlineKeyboardButton(text="Отмена", callback_data="ticket_cancel")]]))


@router.callback_query(F.data == "ticket_cancel")
async def user_close_cancel(callback: CallbackQuery) -> None:
    await callback.answer("Отменено")
    await callback.message.edit_text("Закрытие отменено.")


@router.callback_query(F.data.startswith("ticket_finish:"))
async def user_close_ticket(callback: CallbackQuery) -> None:
    from app.tickets import ticket_rating_keyboard
    try:
        ticket_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректное обращение", show_alert=True)
        return
    updated = await db.close_user_ticket(callback.from_user.id, ticket_id)
    if not updated:
        await callback.answer("Обращение уже закрыто или недоступно", show_alert=True)
        return
    await callback.answer("Обращение закрыто")
    await callback.message.edit_text(f"Обращение №{ticket_id} закрыто.\nОцените помощь: 1 — плохо, 5 — отлично.", reply_markup=ticket_rating_keyboard(ticket_id))


@router.callback_query(F.data.startswith("ticket_rate:"))
async def user_rate_ticket(callback: CallbackQuery) -> None:
    try:
        _, raw_id, raw_rating = callback.data.split(":")
        updated = await db.rate_user_ticket(callback.from_user.id, int(raw_id), int(raw_rating))
    except (ValueError, TypeError):
        updated = None
    if not updated:
        await callback.answer("Оценка уже поставлена или обращение недоступно", show_alert=True)
        return
    await callback.answer("Спасибо за оценку!")
    await callback.message.edit_text(f"Обращение №{updated['id']} закрыто. Ваша оценка: {updated['support_rating']} из 5. Спасибо!")


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


@router.callback_query(F.data.in_({"vpn_feedback:ok", "vpn_feedback:help", "vpn_feedback:later"}))
async def vpn_feedback(callback: CallbackQuery) -> None:
    value = callback.data.split(':')[1]
    await db.save_vpn_feedback(callback.from_user.id, value)
    await callback.answer("Спасибо, учли ваш ответ")
    if value == 'help':
        await callback.message.answer("Напишите, что не работает. Можно приложить скриншот — поддержка поможет разобраться.", reply_markup=help_connect_reply_keyboard())
    elif value == 'later':
        await callback.message.answer("Хорошо, остановили напоминания о возвращении до следующего подключения. Если устройства остаются добавленными, списания продолжаются — ненужные можно удалить в кабинете.")
    else:
        await callback.message.answer("Отлично! Если возникнут вопросы, напишите сюда — поможем.")
