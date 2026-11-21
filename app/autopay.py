"""Автопополнение: CISPay subscriptions that top up the balance by themselves.

The balance and the per-day price stay as they are: the subscription only adds a fixed amount every N days.
CISPay runs the schedule itself (SBP only, we cannot trigger or skip one charge), so we pick N so that the
money comes when about two days of balance are left:

- the first interval runs from the first payment until (balance + amount) is down to two days;
- after activation the interval becomes amount ÷ cost per day, so the balance stays about where it was.

Devices change the cost per day: the hourly pass moves the interval to match (it applies after the next charge).
Every charge, the first one too, arrives as a payment webhook with `subscription_id` and becomes a pay_orders
row «ap-<transaction>» credited like any top-up. The hourly pass also asks CISPay about open subscriptions, so
a lost webhook only delays a charge by an hour. Off by default: `autopay_enabled` in Настройки; admins see it always.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.autopay")
router = Router(name="autopay")

AMOUNTS = (100, 300, 500, 1000)
DEFAULT_AMOUNT = 300
LEAD_DAYS = 2           # the charge should come with about this many days of balance left
MIN_INTERVAL = 7        # CISPay: 7–360 days unless the shop has amount changes switched on
MAX_INTERVAL = 360
OFFER_PAUSE_DAYS = 30   # after «Не сейчас» the offer does not come back for a month
REMIND_HOURS = 30       # remind when the charge is closer than this
SYNC_SECONDS = 3600
MSK = timezone(timedelta(hours=3))
OPEN = ("pending", "active")
REASONS = {
    "unbound_in_bank": "привязку удалили в приложении банка",
    "charges_declined": "банк трижды подряд отклонил списание",
    "first_payment_failed": "первая оплата не прошла",
    "not_activated": "первую оплату так и не провели",
    "cancelled_by_admin": "его выключила поддержка",
}


# ---------- money ----------

def day_cost(devices: int) -> int:
    return max(1, int(get_settings().vpn_day_price_rub)) * max(1, int(devices or 0))


def _clamp(days: int) -> int:
    return max(MIN_INTERVAL, min(MAX_INTERVAL, int(days)))


def steady_interval(amount: int, daily: int) -> int:
    """After activation: one charge pays for as many days as it lasts."""
    return _clamp(int(amount) // max(1, daily))


def first_interval(amount: int, balance: int, daily: int) -> int:
    """From the first payment until about LEAD_DAYS of balance are left."""
    return _clamp((max(0, int(balance)) + int(amount)) // max(1, daily) - LEAD_DAYS)


def amount_options(daily: int) -> list[dict]:
    """The amounts with how long each lasts; one that does not last MIN_INTERVAL days cannot be chosen."""
    return [{"amount": a, "days": a // max(1, daily), "ok": a // max(1, daily) >= MIN_INTERVAL} for a in AMOUNTS]


def default_amount(daily: int) -> int:
    ok = [o["amount"] for o in amount_options(daily) if o["ok"]]
    if DEFAULT_AMOUNT in ok:
        return DEFAULT_AMOUNT
    return ok[0] if ok else AMOUNTS[-1]


# ---------- who may use it ----------

def available(telegram_id: int) -> bool:
    s = get_settings()
    if not s.cispay_configured:
        return False
    return bool(s.autopay_enabled) or int(telegram_id) in s.admin_id_set


async def get(telegram_id: int) -> dict | None:
    row = await db._pool_req().fetchrow("SELECT * FROM autopay WHERE telegram_id=$1", int(telegram_id))
    return dict(row) if row else None


async def by_subscription(subscription_id: str) -> dict | None:
    row = await db._pool_req().fetchrow("SELECT * FROM autopay WHERE subscription_id=$1", str(subscription_id))
    return dict(row) if row else None


async def offer_ok(telegram_id: int) -> bool:
    """Show «Пополнять автоматически» in balance warnings: available, not on, not declined recently."""
    if not available(telegram_id):
        return False
    row = await db._pool_req().fetchrow(
        "SELECT status, COALESCE(declined_until > NOW(), FALSE) AS declined FROM autopay WHERE telegram_id=$1",
        int(telegram_id))
    return not row or (row["status"] not in OPEN and not row["declined"])


async def decline(telegram_id: int) -> None:
    await db._pool_req().execute(
        """INSERT INTO autopay (telegram_id, declined_until) VALUES ($1, NOW() + make_interval(days => $2))
           ON CONFLICT (telegram_id) DO UPDATE SET declined_until = EXCLUDED.declined_until, updated_at = NOW()""",
        int(telegram_id), OFFER_PAUSE_DAYS)


def _ts(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(value) -> str | None:
    dt = _ts(value)
    return dt.isoformat() if dt else None


def _status(raw) -> str:
    return {"PENDING": "pending", "ACTIVE": "active", "PAUSED": "active",
            "CANCELLED": "cancelled", "FAILED": "failed"}.get(str(raw or "").upper(), "pending")


async def _store_remote(sub: dict) -> dict | None:
    """Copy CISPay's view of the subscription into our row; returns the row before the change."""
    before = await by_subscription(str(sub.get("id") or ""))
    if not before:
        return None
    await db._pool_req().execute(
        """UPDATE autopay SET status=$2, interval_days=COALESCE($3, interval_days),
               next_charge_at=$4, last_charge_at=COALESCE($5, last_charge_at),
               ended_reason=COALESCE($6, ended_reason),
               pay_url=CASE WHEN $2='pending' THEN COALESCE($7, pay_url) ELSE NULL END, updated_at=NOW()
           WHERE subscription_id=$1""",
        str(sub["id"]), _status(sub.get("status")), sub.get("interval_days"), _ts(sub.get("next_charge_at")),
        _ts(sub.get("last_charge_at")), sub.get("ended_reason"), sub.get("payment_url"))
    return before


# ---------- turning on and off ----------

async def start(rp, telegram_id: int, amount: int) -> dict:
    """A new subscription; returns {"pay_url"}. The first payment both tops up and switches it on."""
    from app.cispay import CISPayError
    if rp is None or not available(telegram_id):
        raise ValueError("Автопополнение недоступно")
    amount = int(amount)
    devices = await db.billable_device_count(telegram_id)
    daily = day_cost(devices)
    if amount not in AMOUNTS or amount // daily < MIN_INTERVAL:
        raise ValueError("Выберите сумму, которой хватит хотя бы на неделю")
    row = await get(telegram_id)
    if row and row["status"] == "active":
        raise ValueError("Автопополнение уже включено")
    if row and row["status"] == "pending" and row.get("pay_url") and int(row["amount_rub"]) == amount:
        return {"pay_url": row["pay_url"]}
    if row and row["status"] == "pending" and row.get("subscription_id"):
        try:
            await rp.cancel_subscription(row["subscription_id"])
        except CISPayError:
            logger.warning("Old pending autopay %s not cancelled", row["subscription_id"], exc_info=True)
    user = await db.get_user(telegram_id) or {}
    interval = first_interval(amount, int(user.get("balance_rub") or 0), daily)
    sub = await rp.create_subscription(
        amount_rub=amount, interval_days=interval, customer_id=str(telegram_id),
        purpose=f"{get_settings().brand_name}: автопополнение баланса на {amount} ₽")
    await db._pool_req().execute(
        """INSERT INTO autopay (telegram_id, subscription_id, status, amount_rub, interval_days, pay_url,
                                next_charge_at, last_charge_at, ended_reason, reminded_for, failed_tx)
           VALUES ($1, $2, 'pending', $3, $4, $5, NULL, NULL, NULL, NULL, NULL)
           ON CONFLICT (telegram_id) DO UPDATE SET subscription_id=EXCLUDED.subscription_id, status='pending',
               amount_rub=EXCLUDED.amount_rub, interval_days=EXCLUDED.interval_days, pay_url=EXCLUDED.pay_url,
               next_charge_at=NULL, last_charge_at=NULL, ended_reason=NULL, reminded_for=NULL, failed_tx=NULL,
               updated_at=NOW()""",
        int(telegram_id), str(sub["id"]), amount, interval, str(sub["payment_url"]))
    return {"pay_url": str(sub["payment_url"])}


async def stop(rp, telegram_id: int) -> bool:
    """Cancel at CISPay (it also revokes the saved SBP binding). True when something was on."""
    row = await get(telegram_id)
    if not row or row["status"] not in OPEN or not row.get("subscription_id"):
        return False
    if rp is None:
        raise ValueError("Оплата не настроена")
    await rp.cancel_subscription(row["subscription_id"])
    await db._pool_req().execute(
        """UPDATE autopay SET status='cancelled', ended_reason='cancelled_by_user', next_charge_at=NULL,
               pay_url=NULL, updated_at=NOW() WHERE telegram_id=$1""", int(telegram_id))
    return True


# ---------- charges ----------

async def credit_charge(row: dict, tx_id: str, amount_kop: int | None, rw, bot) -> bool:
    """A paid charge of the subscription onto the balance, once per CISPay transaction."""
    from app.billing import fulfill_pay_order, refuse_short_payment
    order_id = f"ap-{tx_id}"
    amount = int(row["amount_rub"])
    await db._pool_req().execute(
        """INSERT INTO pay_orders (order_id, telegram_id, plan_code, payment_id, pay_url, status, method, amount_kop)
           VALUES ($1, $2, $3, $4, '', 'created', 'sbp', $5) ON CONFLICT (order_id) DO NOTHING""",
        order_id, int(row["telegram_id"]), f"b{amount}", f"cis:{tx_id}", amount * 100)
    order = await db.get_pay_order(order_id)
    if not order or order["status"] == "granted":
        return False
    if await refuse_short_payment(order, {"amount": amount_kop, "currency": "RUB"}, bot):
        return False
    await fulfill_pay_order(order_id, rw, bot=bot)
    await db._pool_req().execute(
        "UPDATE autopay SET last_charge_at=NOW(), failed_tx=NULL, updated_at=NOW() WHERE telegram_id=$1",
        int(row["telegram_id"]))
    return True


async def on_payment(event: dict, rp, rw, bot) -> bool:
    """A payment webhook with subscription_id. True when it was ours to handle."""
    row = await by_subscription(str(event.get("subscription_id") or ""))
    if not row:
        return False
    status = str(event.get("status") or "").upper()
    tx = str(event.get("id") or "")
    if status == "PAID" and tx:
        await credit_charge(row, tx, event.get("amount"), rw, bot)
        await refresh(rp, row, bot)
    elif status == "FAILED" and tx and row["status"] == "active" and row.get("failed_tx") != tx:
        await db._pool_req().execute("UPDATE autopay SET failed_tx=$2, updated_at=NOW() WHERE telegram_id=$1",
                                     int(row["telegram_id"]), tx)
        await _send(bot, int(row["telegram_id"]), failed_text(row), _failed_keyboard())
    return True


async def on_event(event: dict, rp, bot) -> None:
    """subscription.activated / cancelled / failed."""
    if not await _apply(event, rp, bot):
        logger.warning("CISPay subscription event for unknown %s", event.get("id"))


async def _apply(sub: dict, rp, bot) -> dict | None:
    """Store CISPay's view and tell the person when it switched on or off (a webhook or the hourly pass)."""
    if not sub.get("id"):
        return None
    before = await _store_remote(sub)
    if not before:
        return None
    uid = int(before["telegram_id"])
    after = await get(uid) or {}
    if before["status"] != "active" and after.get("status") == "active":
        await tune(rp, after)
        after = await get(uid) or after
        await _send(bot, uid, panel_text(after), panel_keyboard(after))
    elif before["status"] in OPEN and after.get("status") not in OPEN:
        reason = str(sub.get("reason") or sub.get("ended_reason") or "")
        quiet = (reason == "cancelled_by_merchant" or before.get("ended_reason") == "cancelled_by_user"
                 or (before["status"] == "pending" and reason in ("not_activated", "first_payment_failed")))
        if not quiet:  # switched off by them, or they never finished turning it on
            await _send(bot, uid, ended_text(reason), _ended_keyboard())
    return before


async def refresh(rp, row: dict | None, bot=None) -> None:
    """Pull the subscription from CISPay: status, next date and any paid charge a webhook missed."""
    if rp is None or not row or not row.get("subscription_id"):
        return
    from app import runtime
    from app.cispay import CISPayError
    bot = bot or runtime.bot
    try:
        sub = await rp.get_subscription(row["subscription_id"])
    except CISPayError:
        logger.warning("Autopay %s not refreshed", row["subscription_id"], exc_info=True)
        return
    for charge in sub.get("charges") or []:
        if str(charge.get("status") or "").upper() == "PAID" and charge.get("id"):
            await credit_charge(row, str(charge["id"]), charge.get("amount"), runtime.rw, bot)
    await _apply(sub, rp, bot)


async def tune(rp, row: dict | None) -> None:
    """Keep the interval at amount ÷ cost per day (devices change it). CISPay applies it after the next charge."""
    if rp is None or not row or row["status"] != "active" or not row.get("subscription_id"):
        return
    want = steady_interval(int(row["amount_rub"]), day_cost(await db.billable_device_count(int(row["telegram_id"]))))
    if want == int(row.get("interval_days") or 0):
        return
    from app.cispay import CISPayError
    try:
        await rp.update_subscription(row["subscription_id"], interval_days=want)
    except CISPayError:
        logger.warning("Autopay %s interval not changed", row["subscription_id"], exc_info=True)
        return
    await db._pool_req().execute("UPDATE autopay SET interval_days=$2, updated_at=NOW() WHERE telegram_id=$1",
                                 int(row["telegram_id"]), want)


# ---------- texts ----------

def _date(dt: datetime | None) -> str:
    dt = _ts(dt)
    if not dt:
        return ""
    from app.return_bonus import MONTHS
    local = dt.astimezone(MSK)
    return f"{local.day} {MONTHS[local.month - 1]}"


def panel_text(row: dict | None) -> str:
    if not row or row["status"] not in OPEN:
        return ("🔁 <b>Автопополнение выключено</b>\n\n"
                "Включите — и баланс будет пополняться сам через СБП, когда его останется примерно на 2 дня.")
    if row["status"] == "pending":
        return (f"🔁 <b>Автопополнение ждёт оплаты</b>\n\nОплатите {row['amount_rub']} ₽ через СБП — "
                "этот платёж пополнит баланс и включит автопополнение.")
    when = _date(row.get("next_charge_at"))
    return (f"🔁 <b>Автопополнение включено</b>\n\n"
            f"{'Следующее пополнение — <b>' + when + '</b>' if when else 'Пополним, когда баланса останется примерно на 2 дня'}, "
            f"{row['amount_rub']} ₽ через СБП.\nЗа день до списания напомним. Отключить можно в любой момент.")


def reminder_text(row: dict) -> str:
    return (f"🔁 <b>Завтра пополним баланс на {row['amount_rub']} ₽</b>\n\n"
            "Деньги спишутся через СБП автоматически, ничего делать не нужно.")


def failed_text(row: dict) -> str:
    return (f"⚠️ <b>Не получилось пополнить баланс на {row['amount_rub']} ₽</b>\n\n"
            "Банк отклонил автоматическое списание. Попробуем ещё раз; после трёх неудач подряд автопополнение "
            "выключится. Чтобы VPN не выключился, можно пополнить вручную.")


def ended_text(reason: str) -> str:
    why = REASONS.get(reason)
    return ("🔁 <b>Автопополнение выключено</b>" + (f": {why}." if why else ".") +
            "\n\nБаланс больше не пополняется сам. Включить снова можно в кабинете.")


def _cabinet_button(text: str, screen: str) -> InlineKeyboardButton | None:
    from app.keyboards import mini_app_screen
    app = mini_app_screen(screen)
    return InlineKeyboardButton(text=text, web_app=app) if app else None


def panel_keyboard(row: dict | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if row and row["status"] == "active":
        rows.append([InlineKeyboardButton(text="Отключить", callback_data="ap:off")])
        btn = _cabinet_button("Подробнее в кабинете", "autopay")
    elif row and row["status"] == "pending" and row.get("pay_url"):
        rows.append([InlineKeyboardButton(text=f"Оплатить {row['amount_rub']} ₽ и включить", url=row["pay_url"])])
        btn = _cabinet_button("Выбрать другую сумму", "autopay")
    else:
        btn = _cabinet_button("Включить", "autopay")
    if btn:
        rows.append([btn])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _reminder_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Хорошо", callback_data="ap:ok"),
        InlineKeyboardButton(text="Отключить", callback_data="ap:off"),
    ]])


def _failed_keyboard() -> InlineKeyboardMarkup:
    btn = _cabinet_button("Пополнить вручную", "topup")
    return InlineKeyboardMarkup(inline_keyboard=[[btn]] if btn else [])


def _ended_keyboard() -> InlineKeyboardMarkup:
    btn = _cabinet_button("Включить снова", "autopay")
    return InlineKeyboardMarkup(inline_keyboard=[[btn]] if btn else [])


def offer_button() -> InlineKeyboardButton | None:
    """«Пополнять автоматически» under balance warnings."""
    return _cabinet_button("🔁 Пополнять автоматически", "autopay")


async def _send(bot, uid: int, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    if bot is None:
        return
    try:
        await bot.send_message(uid, text, reply_markup=markup if markup and markup.inline_keyboard else None)
    except Exception:
        logger.warning("Autopay message to %s not delivered", uid, exc_info=True)


# ---------- the hourly pass ----------

async def remind_due(bot) -> int:
    """«Завтра пополним» once per charge date, in the 10–21 Moscow window."""
    hour = datetime.now(MSK).hour
    if not 10 <= hour < 21:
        return 0
    rows = await db._pool_req().fetch(
        """SELECT * FROM autopay WHERE status='active' AND next_charge_at IS NOT NULL
             AND next_charge_at > NOW() + INTERVAL '1 hour'
             AND next_charge_at < NOW() + make_interval(hours => $1)
             AND reminded_for IS DISTINCT FROM next_charge_at""", REMIND_HOURS)
    sent = 0
    for row in map(dict, rows):
        await db._pool_req().execute("UPDATE autopay SET reminded_for=next_charge_at WHERE telegram_id=$1",
                                     int(row["telegram_id"]))
        await _send(bot, int(row["telegram_id"]), reminder_text(row), _reminder_keyboard())
        sent += 1
    return sent


async def sync_once(rp, bot) -> None:
    rows = await db._pool_req().fetch("SELECT * FROM autopay WHERE status = ANY($1::text[])", list(OPEN))
    for row in map(dict, rows):
        await refresh(rp, row, bot)
        await tune(rp, await get(int(row["telegram_id"])))
    await remind_due(bot)


async def autopay_loop(rp, bot) -> None:
    if rp is None:
        return
    while True:
        try:
            await sync_once(rp, bot)
        except Exception:
            logger.exception("Autopay pass failed")
        await asyncio.sleep(SYNC_SECONDS)


# ---------- the cabinet ----------

async def public(telegram_id: int) -> dict | None:
    """The cabinet's view, or None when autopay is not offered to this person."""
    if not available(telegram_id):
        return None
    row = await get(telegram_id) or {}
    daily = day_cost(await db.billable_device_count(telegram_id))
    status = row.get("status") if row.get("status") in OPEN else "off"
    charges = await db._pool_req().fetch(
        """SELECT o.created_at, o.amount_kop, o.status FROM pay_orders o
           WHERE o.telegram_id=$1 AND o.order_id LIKE 'ap-%' ORDER BY o.created_at DESC LIMIT 5""", int(telegram_id))
    declined = await db._pool_req().fetchval(
        "SELECT COALESCE(declined_until > NOW(), FALSE) FROM autopay WHERE telegram_id=$1", int(telegram_id))
    return {
        "status": status,
        "amount": int(row.get("amount_rub") or 0) or None,
        "next_charge_at": _iso(row.get("next_charge_at")),
        "pay_url": row.get("pay_url") if status == "pending" else None,
        "ended_reason": REASONS.get(str(row.get("ended_reason") or "")) if status == "off" else None,
        "offer": status == "off" and not declined,
        "day_cost": daily,
        "lead_days": LEAD_DAYS,
        "options": amount_options(daily),
        "default": default_amount(daily),
        "charges": [{"at": _iso(c["created_at"]), "amount": int(c["amount_kop"] or 0) // 100,
                     "ok": c["status"] == "granted"} for c in charges],
    }


# ---------- the chat ----------

@router.message(Command("autopay"))
async def cmd_autopay(message: Message) -> None:
    uid = message.from_user.id
    if not available(uid):
        await message.answer("Автопополнение пока недоступно.")
        return
    row = await get(uid)
    await message.answer(panel_text(row), reply_markup=panel_keyboard(row))


@router.callback_query(F.data == "ap:ok")
async def cb_ok(query: CallbackQuery) -> None:
    await query.answer("Хорошо 👍")
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.callback_query(F.data == "ap:off")
async def cb_off(query: CallbackQuery, rp=None) -> None:
    from app.cispay import CISPayError
    try:
        await stop(rp, query.from_user.id)
    except (CISPayError, ValueError):
        logger.warning("Autopay of %s not cancelled from the chat", query.from_user.id, exc_info=True)
        await query.answer("Не получилось отключить, попробуйте позже", show_alert=True)
        return
    await query.answer("Автопополнение выключено")
    try:
        await query.message.edit_text(
            "🔁 <b>Автопополнение выключено</b>\n\nСписаний больше не будет. Включить снова можно в кабинете.",
            reply_markup=_ended_keyboard() if _ended_keyboard().inline_keyboard else None)
    except Exception:
        pass

