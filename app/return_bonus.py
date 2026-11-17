"""«Возвращайтесь с бонусом»: ten days after a paying customer's money ran out, the bot offers +return_bonus_percent
to a top-up from return_bonus_min_rub made within return_bonus_days. The offer is the last step of the «paid-empty»
journey (app/recovery_funnel.py); the credit happens inside db.credit_payment_once, once per offer."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import get_settings

STEP_ID = "recovery-recover-topup-4"
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")
MSK = timezone(timedelta(hours=3))


def terms() -> tuple[int, int, int] | None:
    """(from ₽, percent, days) while the bonus is on, else None."""
    s = get_settings()
    if not s.return_bonus_enabled:
        return None
    return max(1, int(s.return_bonus_min_rub)), max(1, int(s.return_bonus_percent)), max(1, int(s.return_bonus_days))


def bonus_rub(amount: int, percent: int) -> int:
    return max(0, int(amount or 0)) * max(0, int(percent)) // 100


def until_label(sent_at: datetime, days: int) -> str:
    """The last day of the offer in Moscow time: «28 ноября»."""
    end = (sent_at + timedelta(days=days)).astimezone(MSK)
    return f"{end.day} {MONTHS[end.month - 1]}"


def fill(body: str, now: datetime | None = None) -> str | None:
    """The step text with {bonus_min}, {bonus_pct}, {bonus_until}; None when the bonus is off."""
    t = terms()
    if not t:
        return None
    need, pct, days = t
    return (body.replace("{bonus_min}", f"{need} ₽").replace("{bonus_pct}", str(pct))
            .replace("{bonus_total}", f"{need + bonus_rub(need, pct)} ₽")
            .replace("{bonus_until}", until_label(now or datetime.now(timezone.utc), days)))


async def for_payment(conn, telegram_id: int, amount: int) -> int:
    """Rubles to add on top of this top-up: the offer went out within the last return_bonus_days,
    the amount reaches the threshold and nothing was credited for this offer yet."""
    t = terms()
    if not t:
        return 0
    need, pct, days = t
    if int(amount or 0) < need:
        return 0
    sent = await conn.fetchval(
        """SELECT s.sent_at FROM funnel_step_sends s
           WHERE s.telegram_id=$1 AND s.step_id=$2 AND s.sent_at > NOW() - ($3::int * INTERVAL '1 day')
             AND NOT EXISTS (SELECT 1 FROM billing_events b WHERE b.telegram_id=s.telegram_id
                 AND b.kind='return_bonus' AND b.created_at >= s.sent_at)""",
        int(telegram_id), STEP_ID, days)
    return bonus_rub(amount, pct) if sent else 0
