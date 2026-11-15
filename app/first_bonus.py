"""«+10% к первому пополнению»: the first top-up of at least first_bonus_min_rub made before the gift runs out
adds first_bonus_percent of the amount to the balance. The credit itself happens inside db.credit_payment_once."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import get_settings

# A payment opened while the gift was still running counts even if the balance hit zero during checkout.
CHECKOUT_GRACE = timedelta(hours=2)


def bonus_rub(amount: int) -> int:
    """The bonus for this amount: first_bonus_percent of it, rounded down to whole rubles."""
    return max(0, int(amount or 0)) * max(0, int(get_settings().first_bonus_percent)) // 100


def eligible(local: dict | None, *, now: datetime | None = None) -> bool:
    """Gift taken, nothing paid yet, and the gift is still running (or checkout started shortly ago)."""
    s = get_settings()
    if not s.first_bonus_enabled or not local or local.get("has_paid_topup") or not local.get("trial_used"):
        return False
    if int(local.get("balance_rub") or 0) > 0:
        return True
    started = local.get("checkout_started_at")
    if started is None:
        return False
    if getattr(started, "tzinfo", None) is None:
        started = started.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - started <= CHECKOUT_GRACE


def bonus_for_payment(local: dict | None, amount: int) -> int:
    """Rubles to add on top of this payment, or 0."""
    if int(amount or 0) < int(get_settings().first_bonus_min_rub) or not eligible(local):
        return 0
    return bonus_rub(amount)


def offer(local: dict | None, *, balance_rub: int, hours_left: int) -> dict | None:
    """What the cabinet shows: the threshold, the percent and how long the offer lasts."""
    s = get_settings()
    if not s.first_bonus_enabled or not local or local.get("has_paid_topup") or not local.get("trial_used"):
        return None
    if int(balance_rub or 0) <= 0:
        return None
    return {
        "min_rub": int(s.first_bonus_min_rub),
        "percent": int(s.first_bonus_percent),
        "hours_left": max(0, int(hours_left or 0)),
    }
