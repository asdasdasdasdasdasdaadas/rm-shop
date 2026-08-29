from __future__ import annotations

import asyncio

from app import db
from app.config import get_settings
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
    sub_url = user.get("subscriptionUrl") or ""
    lines = [
        f"<b>{title}</b>",
        "",
        f"Действует до: <b>{expire_human(user)}</b>",
    ]
    if sub_url:
        lines.extend(["", "Ссылка подписки:", f"<code>{sub_url}</code>"])
    return "\n".join(lines)


async def grant_plan(telegram_id: int, plan_code: str, rw: RemnawaveClient) -> dict | None:
    settings = get_settings()
    plan = settings.plans.get(plan_code)
    if not plan:
        raise ValueError("unknown plan")
    if settings.balance_enabled:
        await db.add_balance_days(telegram_id, plan["days"])
        return None
    local = await db.get_user(telegram_id)
    panel_id = int(local["remnawave_id"]) if local and local.get("remnawave_id") else None
    user = await rw.extend_subscription(
        telegram_id,
        plan["days"],
        tag="PAID",
        panel_user_id=panel_id,
    )
    await db.save_panel_snapshot(telegram_id, user)
    return user


async def _lock_for(order_id: str) -> asyncio.Lock:
    async with _fulfill_guard:
        lock = _order_locks.get(order_id)
        if lock is None:
            lock = asyncio.Lock()
            _order_locks[order_id] = lock
        return lock


async def fulfill_rollypay_order(order_id: str, rw: RemnawaveClient) -> dict | None:
    lock = await _lock_for(order_id)
    async with lock:
        order = await db.get_rollypay_order(order_id)
        if not order:
            return None
        if order["status"] == "granted":
            return None
        user = await grant_plan(int(order["telegram_id"]), order["plan_code"], rw)
        await db.mark_rollypay_paid(order_id)
        return user
