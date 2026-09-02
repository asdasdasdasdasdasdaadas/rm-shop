from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app import db
from app.balance import sync_user_billing
from app.config import get_settings
from app.remnawave import RemnawaveClient
from app.texts import rub_text

logger = logging.getLogger("rm-shop.story")
CHECK_INTERVAL = 20


async def payout_due_stories(rw: RemnawaveClient, bot: Bot) -> int:
    settings = get_settings()
    amount = int(settings.story_reward_rub or 0)
    minutes = int(settings.story_check_minutes or 0)
    if not (settings.balance_enabled and settings.story_reward_enabled and amount > 0 and minutes > 0):
        return 0
    rows = await db.payout_due_story_rewards(minutes, amount)
    for row in rows:
        telegram_id = int(row["telegram_id"])
        total = int(row["balance_rub"] or 0)
        await db.log_billing_event(
            telegram_id,
            "story",
            source="cron",
            amount=amount,
            balance_after=total,
            note="Награда за историю после проверки",
        )
        try:
            await sync_user_billing(rw, telegram_id, bot)
        except Exception:
            logger.debug("Не удалось синхронизировать биллинг после истории %s", telegram_id, exc_info=True)
        try:
            await bot.send_message(
                telegram_id,
                f"Проверка истории закончилась. На баланс начислено {rub_text(amount)}.",
            )
        except Exception:
            logger.debug("Не удалось написать про награду за историю %s", telegram_id, exc_info=True)
    return len(rows)


async def story_payout_loop(rw: RemnawaveClient, bot: Bot) -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        try:
            n = await payout_due_stories(rw, bot)
            if n:
                logger.info("Награда за историю: %s", n)
        except Exception:
            logger.exception("Не удалось выдать награды за историю")
