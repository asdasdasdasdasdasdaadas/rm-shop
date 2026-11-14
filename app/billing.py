from __future__ import annotations

import asyncio
import logging

from datetime import datetime, timedelta, timezone

from aiogram import Bot

from app import db, runtime
from app.config import get_settings
from app.remnawave import RemnawaveClient, parse_expire, panel_lease_until

logger = logging.getLogger(__name__)

_fulfill_guard = asyncio.Lock()
_order_locks: dict[str, asyncio.Lock] = {}


def expire_human(user: dict | None) -> str:
    if not user:
        return "нет"
    dt = parse_expire(user.get("expireAt"))
    if not dt:
        return "нет"
    return dt.astimezone().strftime("%d.%m.%Y %H:%M")


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
    telegram_id: int, plan_code: str, rw: RemnawaveClient,
    bot: Bot | None = None, payment_key: str | None = None, *, stars: int = 0,
) -> dict | None:
    settings = get_settings()
    plan = settings.plan_by_code(plan_code)
    if not plan or not payment_key:
        raise ValueError("Unknown plan or missing payment key")
    router_days = max(1, int(plan.get("days") or settings.router_days or 30)) if plan.get("router") else 0
    amount = int(round(float(plan.get("rub") or 0))) if router_days else int(plan.get("topup_rub") or 0)
    receipt = await db.credit_payment_once(telegram_id, plan_code, payment_key, amount, router_days, stars)
    if receipt is None:
        return None
    await after_credit(receipt, rw, bot, amount=amount, title=str(plan.get("title") or plan_code))
    return receipt


async def after_credit(receipt: dict, rw: RemnawaveClient, bot: Bot | None, *, amount: int, title: str) -> None:
    """Referral rewards, panel sync, the receipt message and the live event for a committed payment."""
    telegram_id, payment_key = int(receipt["telegram_id"]), receipt["payment_key"]
    # Never expose a side-effect failure as a failed payment after the transaction committed.
    try:
        await apply_payment_effects(receipt, rw, bot)
    except Exception:
        logger.exception("Payment %s credited; effects will retry", payment_key)
    from app.payment_notice import deliver_payment_notice
    try:
        await deliver_payment_notice(bot, receipt)
    except Exception:
        logger.exception("Payment confirmation queued: %s", payment_key)
    from app.live import paid as live_paid
    try:
        local = await db.get_user(telegram_id)
        live_paid(dict(local or {}, telegram_id=telegram_id), amount=amount,
                  title=title, repeat=not receipt['first_payment'])
    except Exception:
        logger.exception("Could not publish payment event %s", payment_key)


async def apply_payment_effects(receipt: dict, rw: RemnawaveClient, bot: Bot | None) -> None:
    key, uid = receipt['payment_key'], int(receipt['telegram_id'])
    if not await db.claim_payment_effects(key):
        return
    from app.balance import sync_user_billing
    from app.referrals import maybe_reward_invitee, maybe_reward_referrer
    local = await db.get_user(uid)
    await maybe_reward_referrer(bot, rw, uid, (local or {}).get('first_name'), payment_key=key,
        topup_rub=receipt['amount'] if not receipt['router_days'] else 0,
        first_payment=receipt['first_payment'], enabled=receipt['referral_enabled'], paid_at=receipt.get('created_at'))
    if receipt['first_payment']:
        await maybe_reward_invitee(bot, uid, enabled=receipt['referral_enabled'], amount=receipt['invitee_bonus'])
    async with runtime.panel_cron_lock():
        if receipt['router_days']:
            await apply_router_slot(rw, uid)
        else:
            await sync_user_billing(rw, uid, bot, source="pay")
    await db.finish_payment_effects(key)


async def payment_effects_loop(rw: RemnawaveClient, bot: Bot) -> None:
    while True:
        try:
            for receipt in await db.pending_payment_effects():
                try:
                    await apply_payment_effects(receipt, rw, bot)
                except Exception:
                    logger.exception("Payment effects will retry: %s", receipt['payment_key'])
        except Exception:
            logger.exception("Could not load pending payment effects")
        try:
            from app.payment_notice import deliver_payment_notice
            for receipt in await db.pending_payment_notices():
                try:
                    await deliver_payment_notice(bot, receipt)
                except Exception:
                    logger.exception("Payment notice retry failed: %s", receipt["payment_key"])
        except Exception:
            logger.exception("Could not load payment confirmations")
        await asyncio.sleep(60)


async def _lock_for(order_id: str) -> asyncio.Lock:
    async with _fulfill_guard:
        lock = _order_locks.get(order_id)
        if lock is None:
            lock = asyncio.Lock()
            _order_locks[order_id] = lock
        return lock


async def fulfill_pay_order(
    order_id: str, rw: RemnawaveClient, bot: Bot | None = None
) -> dict | None:
    lock = await _lock_for(order_id)
    async with lock:
        order = await db.get_pay_order(order_id)
        if not order:
            return None
        if order["status"] == "granted":
            return None
        user = await grant_plan(int(order["telegram_id"]), order["plan_code"], rw, bot=bot, payment_key=f"order:{order_id}")
        return user


RECONCILE_SECONDS = 120
RECONCILE_HOURS = 72
RECONCILE_BATCH = 40


async def refuse_short_payment(order: dict, payment: dict | None, bot: Bot | None) -> bool:
    """True when the paid amount is not the invoiced one: the order is set aside and admins are told."""
    from app.cispay import amount_problem
    problem = amount_problem(order, payment)
    if not problem:
        return False
    logger.error("CISPay order %s not credited: %s", order.get("order_id"), problem)
    await db.mark_order_mismatch(order["order_id"])
    if bot is not None:
        text = (f"⚠️ Оплата не зачислена: {problem}.\nСчёт {order.get('order_id')}, "
                f"пользователь {order.get('telegram_id')}. Проверьте в кассе и зачислите вручную, если всё в порядке.")
        for admin_id in sorted(get_settings().admin_id_set):
            try:
                await bot.send_message(admin_id, text)
            except Exception:
                logger.warning("Админ %s не получил сообщение о сумме оплаты", admin_id, exc_info=True)
    return True


async def reconcile_cispay_orders(rp, rw: RemnawaveClient, bot: Bot | None) -> int:
    """Ask CISPay about unpaid invoices of the last days and credit the paid ones.

    The webhook does this as soon as the payment goes through; this pass covers a webhook that never
    arrived (wrong URL in the shop settings, the server was down). Crediting is idempotent per order."""
    from app.cispay import CISPayError, payment_is_paid
    if rp is None:
        return 0
    credited = 0
    for order in await db.unpaid_cispay_orders(RECONCILE_HOURS, RECONCILE_BATCH):
        try:
            payment = await rp.get_payment(order["payment_id"])
        except CISPayError as exc:
            logger.info("CISPay status of %s is unknown: %s", order["order_id"], exc)
            continue
        if not payment_is_paid(payment):
            if payment.get("status") == "expired":
                await db.mark_order_expired(order["order_id"])
            continue
        if await refuse_short_payment(order, payment, bot):
            continue
        logger.warning("CISPay order %s is paid but was not credited: crediting now", order["order_id"])
        try:
            if await fulfill_pay_order(order["order_id"], rw, bot=bot) is not None:
                credited += 1
        except Exception:
            logger.exception("CISPay reconcile credit failed: %s", order["order_id"])
    return credited


async def cispay_reconcile_loop(rp, rw: RemnawaveClient, bot: Bot) -> None:
    while True:
        try:
            await reconcile_cispay_orders(rp, rw, bot)
        except Exception:
            logger.exception("CISPay reconcile pass failed")
        await asyncio.sleep(RECONCILE_SECONDS)
