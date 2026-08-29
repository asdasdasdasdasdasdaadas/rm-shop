from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app import db
from app.access import is_channel_member
from app.config import get_settings
from app.keyboards import (
    channel_keyboard,
    legal_keyboard,
    legal_text,
    profile_keyboard,
    profile_text,
    welcome_text,
)
from app.remnawave import RemnawaveClient
from app.sync import fetch_panel, has_access

router = Router()


async def ack(callback: CallbackQuery, text: str | None = None, alert: bool = False) -> None:
    try:
        await callback.answer(text, show_alert=alert)
    except TelegramBadRequest:
        pass


def _parse_ref(payload: str | None) -> int | None:
    if not payload:
        return None
    parts = payload.split(maxsplit=1)
    arg = parts[1] if len(parts) > 1 else ""
    if arg.startswith("ref_"):
        raw = arg.removeprefix("ref_")
        if raw.isdigit():
            return int(raw)
    return None


async def show_profile(target: Message | CallbackQuery, rw: RemnawaveClient) -> None:
    message = target.message if isinstance(target, CallbackQuery) else target
    from_user = target.from_user
    settings = get_settings()
    panel = None
    local = None
    if from_user:
        panel = await fetch_panel(rw, from_user.id)
        local = await db.get_user(from_user.id)
    trial_available = bool(settings.trial_enabled and local and not local["trial_used"])
    access = has_access(local, panel)
    text = profile_text(from_user.first_name if from_user else None)
    kb = profile_keyboard(trial_available=trial_available, has_access=access)
    if isinstance(target, CallbackQuery):
        await ack(target)
        try:
            await message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


async def gate_or_continue(event: Message | CallbackQuery) -> bool:
    user = event.from_user
    bot = event.bot
    if not await is_channel_member(bot, user.id):
        text = welcome_text()
        kb = channel_keyboard()
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=kb)
            await ack(event, "Сначала подпишитесь на канал", alert=True)
        else:
            await event.answer(text, reply_markup=kb)
        return False
    local = await db.get_user(user.id)
    if not local or not local["accepted_legal_at"]:
        text = legal_text()
        kb = legal_keyboard()
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                await event.message.answer(text, reply_markup=kb)
            await ack(event)
        else:
            await event.answer(text, reply_markup=kb)
        return False
    return True


@router.message(CommandStart())
async def cmd_start(message: Message, rw: RemnawaveClient) -> None:
    ref = _parse_ref(message.text)
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        referred_by=ref,
    )
    if not await is_channel_member(message.bot, message.from_user.id):
        await message.answer(welcome_text(), reply_markup=channel_keyboard())
        return
    local = await db.get_user(message.from_user.id)
    if not local or not local["accepted_legal_at"]:
        await message.answer(legal_text(), reply_markup=legal_keyboard())
        return
    await show_profile(message, rw)


@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    await db.upsert_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
    )
    if not await is_channel_member(callback.bot, callback.from_user.id, force=True):
        await ack(callback, "Подписка не найдена. Подпишитесь и нажмите ещё раз.", alert=True)
        return
    local = await db.get_user(callback.from_user.id)
    if local and local["accepted_legal_at"]:
        await show_profile(callback, rw)
        return
    await callback.message.edit_text(legal_text(), reply_markup=legal_keyboard())
    await ack(callback, "Подписка подтверждена")


@router.callback_query(F.data == "accept_legal")
async def accept_legal(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await is_channel_member(callback.bot, callback.from_user.id):
        await callback.message.edit_text(welcome_text(), reply_markup=channel_keyboard())
        await ack(callback, "Сначала подпишитесь на канал", alert=True)
        return
    await db.upsert_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
    )
    await db.accept_legal(callback.from_user.id)
    await show_profile(callback, rw)


@router.callback_query(F.data == "profile")
async def open_profile(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await gate_or_continue(callback):
        return
    await show_profile(callback, rw)


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    settings = get_settings()
    if message.from_user.id not in settings.admin_id_set:
        return
    base = (settings.webapp_public_url or "").rstrip("/") or f"http://127.0.0.1:{settings.webapp_port}"
    await message.answer(f"Админка: {base}/admin")
