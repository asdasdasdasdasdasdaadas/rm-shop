from __future__ import annotations

import asyncio

from aiogram import Bot

from app import db
from app.config import get_settings
from app.notices import notice_text, sub_block
from app.remnawave import RemnawaveClient, parse_expire

_fulfill_guard = asyncio.Lock()
_order_locks: dict[str, asyncio.Lock] = {}


def expire_human(user: dict | None) -> str:
    if not user:
        return "нет"
    dt = parse_expire(user.get("expireAt"))
    if not dt:
        return "нет"
    return dt.astimezone().strftime("%d.%m.%Y %H:%M")


def subscription_issued_text(user: dict, title: str) -> str:
    return notice_text(
        "subscription_issued",
        title=title,
        expire=expire_human(user),
        sub_block=sub_block((user or {}).get("subscriptionUrl")),
    )


async def grant_plan(
    telegram_id: int,
    plan_code: str,
    rw: RemnawaveClient,
    bot: Bot | None = None,
) -> dict | None:
    settings = get_settings()
    plan = settings.plan_by_code(plan_code)
    if not plan:
        raise ValueError("unknown plan")
    user = None
    if settings.balance_enabled:
        amount = int(plan.get("topup_rub") or 0)
        if amount < 1:
            raise ValueError("unknown plan")
        await db.add_balance_rub(telegram_id, amount)
    else:
        local = await db.get_user(telegram_id)
        panel_id = int(local["remnawave_id"]) if local and local.get("remnawave_id") else None
        user = await rw.extend_subscription(
            telegram_id,
            plan["days"],
            tag="PAID",
            panel_user_id=panel_id,
        )
        await db.save_panel_snapshot(telegram_id, user)
    await db.mark_paid_topup(telegram_id)
    if bot:
        from app.config import referral_is_payout
        from app.referrals import maybe_reward_referrer

        if referral_is_payout():
            local = await db.get_user(telegram_id)
            await maybe_reward_referrer(bot, rw, telegram_id, (local or {}).get("first_name"))
    return user


async def _lock_for(order_id: str) -> asyncio.Lock:
    async with _fulfill_guard:
        lock = _order_locks.get(order_id)
        if lock is None:
            lock = asyncio.Lock()
            _order_locks[order_id] = lock
        return lock


async def fulfill_rollypay_order(
    order_id: str, rw: RemnawaveClient, bot: Bot | None = None
) -> dict | None:
    lock = await _lock_for(order_id)
    async with lock:
        order = await db.get_rollypay_order(order_id)
        if not order:
            return None
        if order["status"] == "granted":
            return None
        user = await grant_plan(int(order["telegram_id"]), order["plan_code"], rw, bot=bot)
        await db.mark_rollypay_paid(order_id)
        return user
