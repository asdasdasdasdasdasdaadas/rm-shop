from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app import db
from app.config import get_settings, referral_is_payout
from app.keyboards import back_profile_keyboard, share_keyboard, trial_nudge_keyboard
from app.notices import notice_text
from app.referrals import trial_grant_rub
from app.texts import days_text, rub_text

logger = logging.getLogger("rm-shop.nudge")
NUDGE_INTERVAL = 120


def trial_nudge_text(first_name: str | None) -> str:
    settings = get_settings()
    name = first_name or "привет"
    days = days_text(settings.trial_days)
    if settings.balance_enabled:
        extra = (
            f"На баланс сразу ляжет {rub_text(trial_grant_rub())} на {days}."
        )
    else:
        extra = f"Бесплатный период — {days}."
    return notice_text("trial_nudge", name=name, extra=extra)


def invite_nudge_text(telegram_id: int, first_name: str | None) -> str:
    settings = get_settings()
    name = first_name or "привет"
    link = f"https://t.me/{settings.bot_username}?start=ref_{telegram_id}"
    if settings.balance_enabled:
        reward = rub_text(settings.referral_reward_rub)
    else:
        reward = days_text(settings.referral_reward_days)
    if referral_is_payout():
        when = "Когда человек перейдёт по вашей ссылке и первый раз оплатит VPN, бонус придёт вам."
    else:
        when = (
            "Когда человек перейдёт по вашей ссылке и нажмёт «Попробовать бесплатно», "
            "бонус придёт вам обоим."
        )
    return notice_text("invite_nudge", name=name, reward=reward, link=link, when=when)


def info_nudge_text() -> str:
    settings = get_settings()
    story = ""
    if settings.balance_enabled and settings.story_reward_enabled and settings.story_reward_rub > 0:
        story = (
            f"\n\nЗа историю в Telegram можно получить {rub_text(settings.story_reward_rub)} на баланс."
        )
    if settings.balance_enabled:
        price = rub_text(settings.vpn_day_price_rub)
    else:
        price = days_text(1)
    return notice_text("info_nudge", price=price, story=story)


async def send_due_trial_nudges(bot: Bot) -> int:
    settings = get_settings()
    if not settings.trial_enabled:
        return 0
    if not await db.flag_on("trial_nudge"):
        return 0
    if await db.flag_on("maintenance"):
        return 0
    sent = 0
    for row in await db.claim_trial_nudge_batch():
        telegram_id = int(row["telegram_id"])
        try:
            await bot.send_message(
                telegram_id,
                trial_nudge_text(row.get("first_name")),
                reply_markup=trial_nudge_keyboard(),
            )
            sent += 1
        except Exception:
            logger.debug("Напоминание о триале не ушло %s", telegram_id, exc_info=True)
        await asyncio.sleep(0.035)
    return sent


async def send_due_invite_nudges(bot: Bot) -> int:
    if not await db.flag_on("invite_nudge"):
        return 0
    if await db.flag_on("maintenance"):
        return 0
    sent = 0
    for row in await db.claim_invite_nudge_batch():
        telegram_id = int(row["telegram_id"])
        try:
            await bot.send_message(
                telegram_id,
                invite_nudge_text(telegram_id, row.get("first_name")),
                reply_markup=share_keyboard(get_settings().bot_username, telegram_id),
            )
            sent += 1
        except Exception:
            logger.debug("Напоминание пригласить друга не ушло %s", telegram_id, exc_info=True)
        await asyncio.sleep(0.035)
    return sent


async def send_due_info_nudges(bot: Bot) -> int:
    if not await db.flag_on("info_nudge"):
        return 0
    if await db.flag_on("maintenance"):
        return 0
    sent = 0
    kb = back_profile_keyboard(cabinet=True)
    for row in await db.claim_info_nudge_batch():
        telegram_id = int(row["telegram_id"])
        try:
            await bot.send_message(
                telegram_id,
                info_nudge_text(),
                reply_markup=kb,
            )
            sent += 1
        except Exception:
            logger.debug("Справка о кабинете не ушла %s", telegram_id, exc_info=True)
        await asyncio.sleep(0.035)
    return sent


async def trial_nudge_loop(bot: Bot) -> None:
    while True:
        await asyncio.sleep(NUDGE_INTERVAL)
        try:
            n = await send_due_trial_nudges(bot)
            if n:
                logger.info("Напоминание о триале: %s", n)
            n = await send_due_invite_nudges(bot)
            if n:
                logger.info("Напоминание пригласить друга: %s", n)
            n = await send_due_info_nudges(bot)
            if n:
                logger.info("Справка о кабинете: %s", n)
        except Exception:
            logger.exception("Напоминания не удалось отправить")
