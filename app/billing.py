from __future__ import annotations

import asyncio

from datetime import datetime, timedelta, timezone

from aiogram import Bot

from app import db
from app.config import get_settings
from app.notices import notice_text, sub_block
from app.remnawave import RemnawaveClient, parse_expire, panel_lease_until

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


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def router_panel_until(expire_at: datetime) -> datetime:
    now = datetime.now(timezone.utc)
    exp = _aware(expire_at) or now
    left = max(2, int((exp - now).total_seconds() // 86400) + 2)
    return panel_lease_until(min_days=left)


async def apply_router_slot(
    rw: RemnawaveClient,
    telegram_id: int,
    expire_at: datetime | None = None,
) -> None:
    local = await db.get_user(telegram_id)
    exp = _aware(expire_at if expire_at is not None else (local or {}).get("router_expire_at"))
    item = await db.get_router_device(telegram_id)
    if not item or not item.get("remnawave_id"):
        return
    panel_id = int(item["remnawave_id"])
    now = datetime.now(timezone.utc)
    if exp and exp > now:
        until = router_panel_until(exp)
        await rw.set_panel_expire(panel_id, until)
        await db.mark_devices_billed([int(item["id"])], status="ACTIVE", expire_at=until, touch_billed=False)
        return
    try:
        await rw.disable_panel_user(panel_id)
    except Exception:
        return
    await db.mark_devices_billed([int(item["id"])], status="DISABLED", touch_billed=False)


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
    local = await db.get_user(telegram_id)
    repeat = bool(local and local.get("has_paid_topup"))
    user = None
    amount = 0
    if plan.get("router"):
        days = max(1, int(plan.get("days") or settings.router_days or 30))
        try:
            amount = int(round(float(plan.get("rub") or 0)))
        except (TypeError, ValueError):
            amount = int(settings.router_rub or 0)
        expire = await db.extend_router_expire(telegram_id, days)
        await db.log_billing_event(
            telegram_id,
            "router",
            source="pay",
            amount=amount,
            note=plan_code,
        )
        try:
            await apply_router_slot(rw, telegram_id, expire)
        except Exception:
            pass
    elif settings.balance_enabled:
        amount = int(plan.get("topup_rub") or 0)
        if amount < 1:
            raise ValueError("unknown plan")
        await db.add_balance_rub(telegram_id, amount)
        await db.log_billing_event(
            telegram_id,
            "topup",
            source="pay",
            amount=amount,
            note=plan_code,
        )
    else:
        try:
            amount = int(round(float(plan.get("rub") or 0)))
        except (TypeError, ValueError):
            amount = 0
        panel_id = int(local["remnawave_id"]) if local and local.get("remnawave_id") else None
        user = await rw.extend_subscription(
            telegram_id,
            plan["days"],
            tag="PAID",
            panel_user_id=panel_id,
        )
        await db.save_panel_snapshot(telegram_id, user)
    await db.mark_paid_topup(telegram_id)
    from app.live import paid as live_paid

    who = dict(local or {})
    who.setdefault("telegram_id", telegram_id)
    live_paid(
        who,
        amount=amount,
        title=str(plan.get("title") or plan_code),
        repeat=repeat,
    )
    from app.referrals import maybe_reward_invitee, maybe_reward_referrer

    local = await db.get_user(telegram_id)
    await maybe_reward_referrer(bot, rw, telegram_id, (local or {}).get("first_name"))
    await maybe_reward_invitee(bot, telegram_id)
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


async def fulfill_sbp_charge(
    payment: dict,
    rw: RemnawaveClient,
    bot: Bot | None = None,
) -> dict | None:
    payment_id = str(payment.get("payment_id") or "").strip()
    sub_id = str(payment.get("subscription_id") or "").strip()
    if not payment_id or not sub_id:
        return None
    lock = await _lock_for(f"sbp:{payment_id}")
    async with lock:
        sub = await db.get_sbp_subscription_by_id(sub_id)
        if not sub:
            return None
        telegram_id = int(sub["telegram_id"])
        amount = int(sub.get("amount_rub") or 0)
        try:
            paid = payment.get("amount")
            if paid not in (None, ""):
                amount = int(round(float(str(paid).replace(",", "."))))
        except (TypeError, ValueError):
            pass
        if amount < 1:
            return None
        if not await db.claim_sbp_charge(payment_id, sub_id, telegram_id, amount):
            return None
        code = str(sub.get("shop_plan_code") or "")
        plan = get_settings().plan_by_code(code)
        if not plan or int(plan.get("topup_rub") or 0) != amount:
            code = f"b{amount}"
        user = await grant_plan(telegram_id, code, rw, bot=bot)
        await db.mark_sbp_subscription_active(sub_id, payment.get("next_charge_at"))
        return {"user": user, "telegram_id": telegram_id, "amount": amount}
