from __future__ import annotations
from app.funnel_ui import answer_funnel

import asyncio
import logging

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramAPIError
from aiogram.types import LinkPreviewOptions, Message

from app import db
from app.config import get_settings
from app.keyboards import channel_keyboard, legal_text, onboarding_keyboard
from app.notices import notice_text
from app.referrals import trial_is_available
from app.texts import days_text
from app.tg_err import fail_extra

logger = logging.getLogger("rm-shop.welcome")

INTRO_PAUSE = 1.5
STICKER_KV = "welcome_sticker_file_id"
DEFAULT_STICKER = "CAACAgIAAxkBAAEGvvRqovc3xHWk_tb7oHrXUIDKdJ8H2AACCAEAAjDUnRGbJRzV9mdkhT0E"
FALLBACK_SETS = ("UtyaDuck", "GomTTam")


async def _pause(bot: Bot, chat_id: int, seconds: float = INTRO_PAUSE) -> None:
    try:
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        pass
    await asyncio.sleep(seconds)


async def _sticker_candidates() -> list[str]:
    ids: list[str] = []
    for raw in (
        get_settings().welcome_sticker_file_id,
        await db.get_kv(STICKER_KV),
        DEFAULT_STICKER,
    ):
        text = str(raw or "").strip()
        if text and text not in ids:
            ids.append(text)
    return ids


async def _fallback_sticker_id(bot: Bot) -> str:
    cached = (await db.get_kv("welcome_sticker_fallback_id")).strip()
    if cached:
        return cached
    for name in FALLBACK_SETS:
        try:
            pack = await bot.get_sticker_set(name)
        except Exception:
            continue
        stickers = list(pack.stickers or [])
        if not stickers:
            continue
        picked = next((s.file_id for s in stickers if (s.emoji or "") in {"👋", "😊", "🙂"}), None)
        file_id = picked or stickers[0].file_id
        if file_id:
            await db.set_kv("welcome_sticker_fallback_id", file_id)
            return file_id
    return ""


async def send_welcome_sticker(bot: Bot, chat_id: int) -> bool:
    try:
        await bot.send_chat_action(chat_id, ChatAction.CHOOSE_STICKER)
    except Exception:
        pass
    await asyncio.sleep(0.35)
    tried: list[str] = []
    for file_id in await _sticker_candidates():
        tried.append(file_id)
        try:
            await bot.send_sticker(chat_id, file_id)
            return True
        except TelegramAPIError:
            continue
        except Exception:
            logger.debug("Стикер приветствия не ушёл", exc_info=True)
            continue
    fallback = await _fallback_sticker_id(bot)
    if fallback and fallback not in tried:
        try:
            await bot.send_sticker(chat_id, fallback)
            return True
        except Exception:
            logger.debug("Запасной стикер приветствия не ушёл", exc_info=True)
            await db.set_kv("welcome_sticker_fallback_id", "")
    return False


async def _log(telegram_id: int, first_name: str | None, body: str, *, ok: bool, exc: Exception | None = None) -> None:
    await db.log_bot_message(
        kind="welcome_intro",
        source="auto",
        telegram_id=telegram_id,
        first_name=first_name,
        title="Первый запуск",
        body=body,
        status="sent" if ok else "failed",
        extra=fail_extra(exc) if exc else None,
    )


async def send_welcome_intro(
    message: Message,
    *,
    in_channel: bool,
) -> bool:
    """First launch: a sticker, then one message with the gift, the price and the button to take it."""
    bot = message.bot
    user = message.from_user
    if not bot or not user:
        return False
    try:
        await send_welcome_sticker(bot, message.chat.id)
        await _pause(bot, message.chat.id, 0.8)
        await db.complete_welcome_support(user.id)
        text = await send_welcome_continuation(message, user.id, in_channel=in_channel, first_name=user.first_name)
        await _log(user.id, user.first_name, text or "", ok=True)
        return True
    except Exception as exc:
        logger.warning("Приветствие первого запуска не ушло %s", user.id, exc_info=True)
        await _log(user.id, user.first_name, "", ok=False, exc=exc)
        return False


async def send_welcome_continuation(message: Message, telegram_id: int, *, in_channel: bool,
                                    first_name: str | None = None) -> str:
    """The one welcome message: hello and the gift (or «уже на балансе»), price, legal, and two buttons —
    take the gift and connect, or ask for help. Without the required channel, the channel step instead."""
    settings = get_settings()
    in_channel = in_channel or not settings.required_channel_enabled
    granted = None
    if in_channel and trial_is_available(await db.get_user(telegram_id)):
        from app import auto_gift
        granted = await auto_gift.grant_if_auto(telegram_id)
    local = await db.get_user(telegram_id) or {}
    trial_on = trial_is_available(local)
    days = days_text(settings.trial_days)
    name = (first_name or local.get("first_name") or "").strip() or "привет"
    if granted is not None:
        from app import auto_gift
        parts = [notice_text("welcome_intro_hi_plain", name=name), auto_gift.granted_text()]
    elif trial_on:
        parts = [notice_text("welcome_intro_hi", name=name, days=days)]
    else:
        parts = [notice_text("welcome_intro_hi_plain", name=name), notice_text("welcome_intro_try_no_trial")]
    if getattr(settings, "welcome_tariff_enabled", True):
        from app.keyboards import tariff_block
        parts.append(tariff_block(referral=False))
    referral_bonus = bool(settings.referral_program_enabled and local.get("referred_by")
                          and not local.get("referral_menu_bonus_at"))
    if referral_bonus:
        parts.append("Вы пришли по ссылке друга — откройте главное меню, и мы сразу начислим вам 50 ₽.")
    if not in_channel:
        parts.append(notice_text("welcome_intro_channel"))
        kb = channel_keyboard()
    else:
        kb = onboarding_keyboard(gift=trial_on and granted is None)
        first = kb.inline_keyboard[0][0].model_copy(update={
            "text": "🎁 Забрать подарок и подключиться" if trial_on and granted is None else "Подключить VPN",
            "style": "success"})
        rows = [[first], *kb.inline_keyboard[1:]]
        if referral_bonus:
            from aiogram.types import InlineKeyboardButton
            rows.append([InlineKeyboardButton(text="Главное меню", callback_data="profile")])
        kb = kb.model_copy(update={"inline_keyboard": rows})
    parts.append(legal_text())
    text = "\n\n".join(p for p in parts if p)
    await answer_funnel(message, text, reply_markup=kb, preserve=in_channel,
                        link_preview_options=LinkPreviewOptions(is_disabled=True))
    await db.mark_legal_notice(telegram_id)
    return text
