"""«+3 дня за первую оплату»: the first top-up of at least first_bonus_min_rub made before the gift runs out
adds first_bonus_days of VPN to the balance. The credit itself happens inside db.credit_payment_once."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import get_settings

# A payment opened while the gift was still running counts even if the balance hit zero during checkout.
CHECKOUT_GRACE = timedelta(hours=2)


def bonus_rub(devices: int) -> int:
    """The gift days in rubles: days × the day price × the devices that are billed."""
    s = get_settings()
    return max(0, int(s.first_bonus_days)) * max(1, int(s.vpn_day_price_rub)) * max(1, int(devices or 0))


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


def bonus_for_payment(local: dict | None, amount: int, devices: int) -> int:
    """Rubles to add on top of this payment, or 0."""
    if int(amount or 0) < int(get_settings().first_bonus_min_rub) or not eligible(local):
        return 0
    return bonus_rub(devices)


def offer(local: dict | None, *, balance_rub: int, hours_left: int, devices: int) -> dict | None:
    """What the cabinet shows: the threshold, the days and how long the offer lasts."""
    s = get_settings()
    if not s.first_bonus_enabled or not local or local.get("has_paid_topup") or not local.get("trial_used"):
        return None
    if int(balance_rub or 0) <= 0:
        return None
    return {
        "min_rub": int(s.first_bonus_min_rub),
        "days": int(s.first_bonus_days),
        "rub": bonus_rub(devices),
        "hours_left": max(0, int(hours_left or 0)),
    }
