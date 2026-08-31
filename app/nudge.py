from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app import db
from app.config import get_settings
from app.keyboards import trial_nudge_keyboard
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


async def trial_nudge_loop(bot: Bot) -> None:
    while True:
        await asyncio.sleep(NUDGE_INTERVAL)
        try:
            n = await send_due_trial_nudges(bot)
            if n:
                logger.info("Напоминание о триале: %s", n)
        except Exception:
            logger.exception("Напоминание о триале не удалось")
