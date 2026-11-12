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
from app.keyboards import with_referral_share
from app.keyboards import channel_keyboard, legal_text, onboarding_keyboard, profile_keyboard
from app.notices import notice_text
from app.referrals import trial_is_available
from app.texts import days_text, rub_text
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
    bot = message.bot
    user = message.from_user
    if not bot or not user:
        return False
    settings = get_settings()
    name = (user.first_name or "").strip() or "привет"
    brand = settings.brand_name
    chat_id = message.chat.id
    local = await db.get_user(user.id)
    hello = notice_text("welcome_intro_hello", name=name, brand=brand)
    if getattr(settings, "welcome_tariff_enabled", True):
        from app.keyboards import tariff_block
        hello += "\n\n" + tariff_block()
    referral_bonus = (settings.referral_program_enabled and local and local.get("referred_by")
                      and not local.get("referral_menu_bonus_at"))
    if referral_bonus:
        hello += "\n\nВы пришли по ссылке друга — откройте меню бота, и мы сразу начислим вам 50 ₽."
    trial_on = trial_is_available(local)
    days = days_text(settings.trial_days)
    hi = (
        notice_text("welcome_intro_hi", name=name, days=days)
        if trial_on
        else notice_text("welcome_intro_hi_plain", name=name)
    )
    parts = [hi, hello]
    try:
        await send_welcome_sticker(bot, chat_id)
        await _pause(bot, chat_id)
        # The intro is a plain story: the cabinet and the gift come with the next message.
        await answer_funnel(message, hi, preserve=True)
        await _pause(bot, chat_id)
        await answer_funnel(message, hello, reply_markup=with_referral_share(user.id) if referral_bonus else None,
                            preserve=True)
        await _pause(bot, chat_id)
        # Straight to the gift and the cabinet: no «Будем на связи» step in between.
        await db.complete_welcome_support(user.id)
        await send_welcome_continuation(message, user.id, in_channel=in_channel)
        await _log(user.id, user.first_name, "\n\n".join(parts), ok=True)
        return True
    except Exception as exc:
        logger.warning("Приветствие первого запуска не ушло %s", user.id, exc_info=True)
        await _log(user.id, user.first_name, "\n\n".join(parts), ok=False, exc=exc)
        return False


async def send_welcome_continuation(message: Message, telegram_id: int, *, in_channel: bool) -> None:
    settings=get_settings()
    in_channel = in_channel or not settings.required_channel_enabled
    local=await db.get_user(telegram_id)
    trial_on=trial_is_available(local)
    days=days_text(settings.trial_days)
    if trial_on:
        try_body = notice_text("welcome_intro_try", days=days)
    else:
        try_body = notice_text("welcome_intro_try_no_trial")
    if not in_channel:
        last = notice_text("welcome_intro_channel")
        kb = channel_keyboard()
    else:
        last = try_body
        kb = profile_keyboard(
            trial_available=trial_on,
            has_access=bool(local and local.get("balance_rub")),
            story_offer=False,
        )
    if in_channel:
        from app.funnel_board import menu_content
        custom = await menu_content((local or {}).get("first_name"), int((local or {}).get("balance_rub") or 0), telegram_id)
        if custom:
            kb = custom[1]
        if trial_on:
            # The hottest moment of the funnel: put the gift one tap away, above the menu.
            gift = onboarding_keyboard(gift=True).inline_keyboard[0][0]
            gift = gift.model_copy(update={"style": "success"})
            kb = kb.model_copy(update={"inline_keyboard": [[gift], *kb.inline_keyboard]}) if kb else onboarding_keyboard(gift=True)
    last += "\n\n" + legal_text()
    await answer_funnel(message, last, reply_markup=kb, preserve=in_channel, link_preview_options=LinkPreviewOptions(is_disabled=True))
    await db.mark_legal_notice(telegram_id)
