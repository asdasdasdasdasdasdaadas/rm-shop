from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from app import db
from app.access import is_channel_member
from app.config import get_settings
from app.live import invited as live_invited
from app.keyboards import (
    channel_keyboard,
    profile_keyboard,
    profile_text,
    welcome_text,
)
from app.referrals import trial_is_available
from app.welcome import send_welcome_intro
from app.remnawave import RemnawaveClient
from app.sync import fetch_panel, has_access

async def _maybe_live_invite(row: dict | None) -> None:
    if not row or not row.get("referral_attached") or not row.get("referred_by"):
        return
    referrer = await db.get_user(int(row["referred_by"]))
    live_invited(referrer, row)


router = Router()


async def ack(callback: CallbackQuery, text: str | None = None, alert: bool = False) -> None:
    try:
        await callback.answer(text, show_alert=alert)
    except TelegramBadRequest:
        pass


def _parse_ref(payload: str | None) -> int | None:
    raw = (payload or "").strip()
    if raw.startswith("/start"):
        parts = raw.split(maxsplit=1)
        raw = parts[1] if len(parts) > 1 else ""
    if raw.startswith("ref_"):
        raw = raw.removeprefix("ref_")
        if raw.isdigit():
            return int(raw)
    return None


def _parse_ad(payload: str | None) -> str | None:
    raw = (payload or "").strip()
    if raw.startswith("/start"):
        parts = raw.split(maxsplit=1)
        raw = parts[1] if len(parts) > 1 else ""
    if not raw.startswith("ad_"):
        return None
    slug = raw[3:].strip().lower()
    if re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", slug) and 2 <= len(slug) <= 32:
        return slug
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
    trial_available = trial_is_available(local)
    access = has_access(local, panel)
    text = profile_text(
        from_user.first_name if from_user else None,
        balance_rub=int((local or {}).get("balance_rub") or 0) if local else 0,
    )
    kb = profile_keyboard(
        trial_available=trial_available,
        has_access=access,
        story_offer=bool(
            settings.balance_enabled
            and settings.story_reward_enabled
            and settings.story_reward_rub > 0
            and local
            and local.get("first_online_at")
            and not local.get("story_rewarded_at")
            and not local.get("story_pending_at")
        ),
    )
    if isinstance(target, CallbackQuery):
        await ack(target)
        try:
            await message.edit_text(
                text, reply_markup=kb, link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except TelegramBadRequest:
            await message.answer(
                text, reply_markup=kb, link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
    else:
        await message.answer(
            text, reply_markup=kb, link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    if from_user:
        await db.mark_legal_notice(from_user.id)


async def gate_or_continue(event: Message | CallbackQuery) -> bool:
    user = event.from_user
    bot = event.bot
    if not await is_channel_member(bot, user.id):
        text = welcome_text()
        kb = channel_keyboard()
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                text, reply_markup=kb, link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            await ack(event, "Сначала подпишитесь на канал", alert=True)
        else:
            await event.answer(
                text, reply_markup=kb, link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        await db.mark_legal_notice(user.id)
        return False
    await db.accept_legal_after_notice(user.id)
    return True


@router.message(CommandStart())
async def cmd_start(message: Message, rw: RemnawaveClient, command: CommandObject) -> None:
    payload = command.args or message.text
    ref = _parse_ref(payload)
    ad_id = None
    slug = _parse_ad(payload)
    if slug:
        ad_id = await db.touch_ad_link(slug)
    row = await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        referred_by=ref,
        ad_link_id=ad_id,
    )
    await _maybe_live_invite(row)
    in_channel = await is_channel_member(message.bot, message.from_user.id)
    if await db.claim_welcome_intro(message.from_user.id):
        ok = await send_welcome_intro(
            message,
            in_channel=in_channel,
        )
        if ok:
            return
    if not in_channel:
        await message.answer(
            welcome_text(), reply_markup=channel_keyboard(), link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        await db.mark_legal_notice(message.from_user.id)
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
    await db.accept_legal_after_notice(callback.from_user.id)
    await show_profile(callback, rw)


@router.callback_query(F.data == "accept_legal")
async def accept_legal(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    if not await is_channel_member(callback.bot, callback.from_user.id):
        await callback.message.edit_text(
            welcome_text(), reply_markup=channel_keyboard(), link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
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


@router.callback_query(F.data == "try_again")
async def try_again(callback: CallbackQuery, rw: RemnawaveClient) -> None:
    user = callback.from_user
    await ack(callback)
    await db.upsert_user(user.id, user.username, user.first_name)
    if not await is_channel_member(callback.bot, user.id):
        await callback.message.answer(
            welcome_text(), reply_markup=channel_keyboard(), link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        await db.mark_legal_notice(user.id)
        return
    await db.accept_legal_after_notice(user.id)
    await show_profile(callback, rw)


@router.message(Command("welcome_sticker"))
async def cmd_welcome_sticker(message: Message) -> None:
    settings = get_settings()
    if message.from_user.id not in settings.admin_id_set:
        return
    sticker = None
    replied = message.reply_to_message
    if replied and replied.sticker:
        sticker = replied.sticker
    elif message.sticker:
        sticker = message.sticker
    if not sticker:
        await message.answer(
            "Ответьте командой /welcome_sticker на стикер — его покажем при первом запуске бота."
        )
        return
    await db.set_welcome_sticker_file_id(sticker.file_id)
    await message.answer("Стикер для первого запуска сохранён.")


@router.message(Command("info"))
async def cmd_info(message: Message) -> None:
    await message.answer("Platega test")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    settings = get_settings()
    if message.from_user.id not in settings.admin_id_set:
        return
    base = (settings.webapp_public_url or "").rstrip("/") or f"http://127.0.0.1:{settings.webapp_port}"
    await message.answer(f"Админка: {base}/admin")
