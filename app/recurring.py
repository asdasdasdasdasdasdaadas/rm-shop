from __future__ import annotations

import logging
import time
from typing import Any

from app.rollypay import RollyPayClient, RollyPayError

logger = logging.getLogger("rm-shop.recurring")

INTERVALS = ("month", "quarter", "year")
INTERVAL_LABELS = {
    "month": "раз в месяц",
    "quarter": "раз в 3 месяца",
    "year": "раз в год",
}
INTERVAL_CAPS = {
    "month": 4000,
    "quarter": 9000,
    "year": 24000,
}

_plans_at = 0.0
_plans: list[dict] = []


def interval_ok(value: str) -> bool:
    return str(value or "").strip() in INTERVALS


def cap_for(interval: str) -> int:
    return int(INTERVAL_CAPS.get(str(interval or "").strip()) or 0)


async def subscription_plans(rp: RollyPayClient | None, *, force: bool = False) -> list[dict]:
    global _plans_at, _plans
    if rp is None:
        return []
    now = time.monotonic()
    if not force and _plans and now - _plans_at < 300:
        return _plans
    try:
        items = await rp.list_subscription_plans()
    except RollyPayError:
        logger.warning("Сценарии регулярных списаний недоступны", exc_info=True)
        return _plans
    except Exception:
        logger.exception("Не удалось получить сценарии регулярных списаний")
        return _plans
    cleaned: list[dict] = []
    for item in items:
        interval = str(item.get("interval") or "").strip()
        plan_id = str(item.get("id") or "").strip()
        if interval not in INTERVALS or not plan_id:
            continue
        cap_raw = item.get("cap_amount_rub")
        try:
            cap = int(round(float(str(cap_raw).replace(",", ".")))) if cap_raw not in (None, "") else cap_for(interval)
        except (TypeError, ValueError):
            cap = cap_for(interval)
        cleaned.append(
            {
                "id": plan_id,
                "interval": interval,
                "code": str(item.get("code") or ""),
                "cap": cap or cap_for(interval),
            }
        )
    _plans = cleaned
    _plans_at = now
    return _plans


def plan_for_interval(plans: list[dict], interval: str) -> dict | None:
    key = str(interval or "").strip()
    for item in plans:
        if item.get("interval") == key:
            return item
    return None


def public_recurring(
    plans: list[dict],
    active: dict | None = None,
    *,
    configured: bool = False,
) -> dict[str, Any]:
    by_interval = {str(item.get("interval") or ""): item for item in plans}
    intervals = []
    for key in INTERVALS:
        scene = by_interval.get(key) or {}
        intervals.append(
            {
                "id": key,
                "label": INTERVAL_LABELS[key].capitalize(),
                "cap": int(scene.get("cap") or cap_for(key)),
            }
        )
    out: dict[str, Any] = {
        "available": True,
        "configured": bool(configured),
        "intervals": intervals,
        "caps": {k: cap_for(k) for k in INTERVALS},
        "active": None,
    }
    if active:
        nxt = active.get("next_charge_at")
        out["active"] = {
            "interval": str(active.get("interval") or ""),
            "amount_rub": int(active.get("amount_rub") or 0),
            "next_charge_at": nxt.isoformat() if hasattr(nxt, "isoformat") else nxt,
            "status": str(active.get("status") or ""),
        }
    return out
