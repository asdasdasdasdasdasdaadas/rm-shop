from __future__ import annotations

from datetime import datetime, timedelta, timezone

import asyncpg

from app import db
from app.config import get_settings
from app.notices import notice_text
from app.texts import rub_text

MAINTENANCE_TEXT = "Сейчас ведутся технические работы. Сервис временно недоступен."


def daily_cost_rub(device_count: int, price: int | None = None) -> int:
    day = max(1, price if price is not None else get_settings().vpn_day_price_rub)
    return day * max(0, int(device_count or 0))


def one_device_day_rub(price: int | None = None) -> int:
    return max(1, price if price is not None else get_settings().vpn_day_price_rub)


def trust_days() -> int:
    return max(1, int(get_settings().trust_days or 1))


def trust_fee_rub() -> int:
    return max(0, int(get_settings().trust_fee_rub or 0))


def trust_credit_rub(price: int | None = None) -> int:
    return trust_days() * one_device_day_rub(price)


def trust_repay_rub(price: int | None = None) -> int:
    return trust_credit_rub(price) + trust_fee_rub()


def _json_loan(row: dict | None) -> dict | None:
    if not row:
        return None
    due = row.get("due_at")
    return {
        "id": row.get("id"),
        "amount": int(row.get("amount") or 0),
        "due_at": due.isoformat() if hasattr(due, "isoformat") else due,
    }


async def trust_info(telegram_id: int, local: dict | None, device_count: int) -> dict:
    settings = get_settings()
    day = one_device_day_rub(settings.vpn_day_price_rub)
    days = trust_days()
    fee = trust_fee_rub()
    credit = trust_credit_rub(settings.vpn_day_price_rub)
    repay = trust_repay_rub(settings.vpn_day_price_rub)
    open_loan = await db.open_trust_loan(telegram_id) if local else None
    balance = int((local or {}).get("balance_rub") or 0)
    paid = bool((local or {}).get("has_paid_topup"))
    reason = ""
    available = False
    enabled = bool(settings.balance_enabled and settings.trust_enabled)
    if not settings.balance_enabled:
        reason = "Обещанный платёж доступен только в режиме баланса"
    elif not settings.trust_enabled:
        reason = "Обещанный платёж выключен"
    elif open_loan:
        reason = "Уже есть незакрытый обещанный платёж"
    elif not paid:
        reason = "Сначала нужно хотя бы раз пополнить баланс. Рефералы и бонусы не считаются"
    elif device_count < 1:
        reason = "Сначала добавьте устройство"
    elif balance > day:
        reason = "Баланс ещё не близок к нулю"
    else:
        available = True
    return {
        "enabled": enabled,
        "available": available,
        "reason": reason,
        "amount": credit,
        "fee": fee,
        "repay": repay,
        "days": days,
        "daily_cost": day,
        "open": _json_loan(open_loan),
    }


async def take_trust(telegram_id: int) -> dict:
    settings = get_settings()
    if not settings.balance_enabled or not settings.trust_enabled:
        raise ValueError("Обещанный платёж недоступен")
    local = await db.get_user(telegram_id)
    if not local:
        raise ValueError("Пользователь не найден")
    n = await db.device_count(telegram_id)
    info = await trust_info(telegram_id, local, n)
    if not info["available"]:
        raise ValueError(info["reason"] or "Нельзя взять обещанный платёж")
    due = datetime.now(timezone.utc) + timedelta(days=int(info["days"]))
    try:
        loan = await db.take_trust_loan(telegram_id, info["amount"], due, info["repay"])
    except asyncpg.exceptions.UniqueViolationError as exc:
        raise ValueError("Уже есть незакрытый обещанный платёж") from exc
    except Exception as exc:
        raise ValueError("Не удалось оформить обещанный платёж") from exc
    await db.log_billing_event(
        telegram_id,
        "trust",
        source="user",
        amount=int(info["repay"]),
        note=f"Обещанный платёж: {info['days']} дн. + комиссия {info['fee']} ₽",
    )
    return _json_loan(loan) or {"amount": info["amount"], "due_at": due.isoformat()}


async def collect_due_trusts(bot) -> None:
    for loan in await db.due_trust_loans():
        tg_id = int(loan["telegram_id"])
        amount = int(loan["amount"] or 0)
        try:
            await db.collect_trust_loan(int(loan["id"]), tg_id, amount)
            await db.log_billing_event(
                tg_id,
                "trust_collect",
                source="cron",
                amount=-abs(amount),
                note="Списание обещанного платежа",
            )
        except Exception:
            continue
        if bot:
            try:
                await bot.send_message(
                    tg_id,
                    notice_text("trust_collect", amount=rub_text(amount)),
                )
            except Exception:
                pass
