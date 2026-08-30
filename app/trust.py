from __future__ import annotations

from datetime import datetime, timedelta, timezone

import asyncpg

from app import db
from app.config import get_settings
from app.texts import rub_text

TRUST_DAYS = 3
MAINTENANCE_TEXT = "Сейчас ведутся технические работы. Сервис временно недоступен."


def daily_cost_rub(device_count: int, price: int | None = None) -> int:
    day = max(1, price if price is not None else get_settings().vpn_day_price_rub)
    return day * max(1, device_count)


def trust_amount_rub(device_count: int, price: int | None = None) -> int:
    return TRUST_DAYS * daily_cost_rub(device_count, price)


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
    amount = trust_amount_rub(device_count, settings.vpn_day_price_rub)
    daily = daily_cost_rub(device_count, settings.vpn_day_price_rub)
    open_loan = await db.open_trust_loan(telegram_id) if local else None
    balance = int((local or {}).get("balance_rub") or 0)
    paid = bool((local or {}).get("has_paid_topup"))
    reason = ""
    available = False
    if not settings.balance_enabled:
        reason = "Доверительный платёж доступен только в режиме баланса"
    elif open_loan:
        reason = "Уже есть незакрытый доверительный платёж"
    elif not paid:
        reason = "Сначала нужно хотя бы раз пополнить баланс. Рефералы и бонусы не считаются"
    elif balance > daily:
        reason = "Баланс ещё не близок к минимуму"
    else:
        available = True
    return {
        "available": available,
        "reason": reason,
        "amount": amount,
        "days": TRUST_DAYS,
        "daily_cost": daily,
        "open": _json_loan(open_loan),
    }


async def take_trust(telegram_id: int) -> dict:
    settings = get_settings()
    if not settings.balance_enabled:
        raise ValueError("Доверительный платёж недоступен")
    local = await db.get_user(telegram_id)
    if not local:
        raise ValueError("Пользователь не найден")
    n = await db.device_count(telegram_id)
    info = await trust_info(telegram_id, local, n)
    if not info["available"]:
        raise ValueError(info["reason"] or "Нельзя взять доверительный платёж")
    due = datetime.now(timezone.utc) + timedelta(days=TRUST_DAYS)
    try:
        loan = await db.take_trust_loan(telegram_id, info["amount"], due)
    except asyncpg.exceptions.UniqueViolationError as exc:
        raise ValueError("Уже есть незакрытый доверительный платёж") from exc
    except Exception as exc:
        raise ValueError("Не удалось оформить доверительный платёж") from exc
    return _json_loan(loan) or {"amount": info["amount"], "due_at": due.isoformat()}


async def collect_due_trusts(bot) -> None:
    for loan in await db.due_trust_loans():
        tg_id = int(loan["telegram_id"])
        amount = int(loan["amount"] or 0)
        try:
            await db.collect_trust_loan(int(loan["id"]), tg_id, amount)
        except Exception:
            continue
        if bot:
            try:
                await bot.send_message(
                    tg_id,
                    f"Списан доверительный платёж: {rub_text(amount)}. "
                    "Если баланс ушёл в минус, пополните его.",
                )
            except Exception:
                pass
