"""A/B test: the start gift goes to the balance by itself instead of waiting for «Забрать подарок».

While a test runs, every new person (started the bot after the test began) is put in one group for good the
first time the bot shows them the gift offer (the welcome message or the main menu):
  auto   — the gift days are credited at once; the message says so and points to «Подключить VPN»;
  manual — as before, the gift waits for the «Забрать подарок» button.
The days are not spent before the first connection (trial_waiting_connection), so an early gift costs nothing
to those who never connect. Results count connections and payments within WINDOW_DAYS of entering the test.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app import db

logger = logging.getLogger("rm-shop.auto_gift")

WINDOW_DAYS = 14
ARMS = ("auto", "manual")
ARM_LABELS = {"auto": "Подарок сразу на балансе", "manual": "Подарок по кнопке (как раньше)"}
AUTO_PCT = 50


async def running() -> dict | None:
    row = await db._pool_req().fetchrow(
        "SELECT * FROM auto_gift_tests WHERE stopped_at IS NULL ORDER BY id DESC LIMIT 1")
    return dict(row) if row else None


async def start() -> int:
    if await running():
        raise ValueError("Тест уже идёт")
    return int(await db._pool_req().fetchval("INSERT INTO auto_gift_tests DEFAULT VALUES RETURNING id"))


async def stop() -> bool:
    return (await db._pool_req().execute(
        "UPDATE auto_gift_tests SET stopped_at=NOW() WHERE stopped_at IS NULL")).endswith(" 1")


async def arm_of(telegram_id: int, local: dict | None) -> str | None:
    """The person's group in the running test, assigning it on first sight; None outside a test."""
    test = await running()
    if not test or not local:
        return None
    started = local.get("bot_started_at")
    if started is None:
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if started < test["started_at"]:
        return None  # only people who came after the start, so the groups are alike
    from app.experiments import bucket
    arm = "auto" if bucket(int(test["id"]), int(telegram_id), "auto_gift") < AUTO_PCT else "manual"
    return await db._pool_req().fetchval(
        """INSERT INTO auto_gift_arms (telegram_id, test_id, arm) VALUES ($1, $2, $3)
           ON CONFLICT (telegram_id) DO UPDATE SET telegram_id=EXCLUDED.telegram_id RETURNING arm""",
        int(telegram_id), int(test["id"]), arm)


async def grant_if_auto(telegram_id: int) -> int | None:
    """In the «auto» group: credit the start gift now. Returns the new balance, or None when nothing was given."""
    from app import runtime
    from app.referrals import trial_grant_rub, trial_is_available
    try:
        local = await db.get_user(telegram_id)
        if not trial_is_available(local) or await arm_of(telegram_id, local) != "auto":
            return None
        async with runtime.panel_cron_lock():
            amount = trial_grant_rub()
            after = await db.claim_trial_balance(telegram_id, amount)
            if after is None:
                return None
            await db.log_billing_event(telegram_id, "trial", source="auto", amount=amount, balance_after=after,
                                       note="Подарок сразу на балансе (A/B-тест)")
            await db._pool_req().execute(
                "UPDATE auto_gift_arms SET granted_at=NOW() WHERE telegram_id=$1", int(telegram_id))
        return after
    except Exception:
        logger.exception("Подарок сразу не начислился %s", telegram_id)
        return None


def granted_text() -> str:
    from app.config import get_settings
    from app.texts import days_text
    days = days_text(get_settings().trial_days)
    return (f"🎁 <b>Подарок уже на балансе: {days} VPN.</b>\n\n"
            "Подключите устройство — дни начнут тратиться только после первого подключения.")


RESULTS_SQL = f"""
WITH per_user AS (
    SELECT a.test_id, a.arm, a.telegram_id,
        a.assigned_at <= NOW() - INTERVAL '{WINDOW_DAYS} days' AS matured,
        COALESCE(u.trial_used, FALSE) AS took_gift,
        EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = a.telegram_id
            AND d.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS device,
        (u.first_online_at IS NOT NULL AND u.first_online_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS connected,
        (SELECT COUNT(*) FROM payment_receipts p WHERE p.telegram_id = a.telegram_id
            AND p.created_at >= a.assigned_at AND p.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS payments,
        (SELECT COALESCE(SUM(p.amount), 0) FROM payment_receipts p WHERE p.telegram_id = a.telegram_id
            AND p.created_at >= a.assigned_at AND p.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS rub
    FROM auto_gift_arms a JOIN users u ON u.telegram_id = a.telegram_id
    WHERE a.test_id = ANY($1::bigint[])
)
SELECT test_id, arm, COUNT(*)::int AS users, COUNT(*) FILTER (WHERE matured)::int AS matured,
    COUNT(*) FILTER (WHERE took_gift)::int AS took_gift, COUNT(*) FILTER (WHERE device)::int AS device,
    COUNT(*) FILTER (WHERE connected)::int AS connected, COUNT(*) FILTER (WHERE payments > 0)::int AS payers,
    COALESCE(SUM(rub), 0)::bigint AS rub
FROM per_user GROUP BY test_id, arm
"""


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def summarize(rows: dict[str, dict]) -> dict:
    from app.experiments import compare, p_value
    items = []
    for arm in ARMS:
        data = {k: int(v) for k, v in (rows.get(arm) or {}).items() if k not in {"test_id", "arm"}}
        for key in ("users", "matured", "took_gift", "device", "connected", "payers", "rub"):
            data.setdefault(key, 0)
        n = data["users"]
        data.update(arm=arm, label=ARM_LABELS[arm], conversion=_pct(data["payers"], n),
                    connected_pct=_pct(data["connected"], n), rub_per_user=round(data["rub"] / n, 1) if n else 0.0)
        items.append(data)
    auto, manual = items
    verdicts = []
    if auto["users"] and manual["users"]:
        diff = auto["connected_pct"] - manual["connected_pct"]
        pv = p_value(auto["connected"], auto["users"], manual["connected"], manual["users"])
        sure = min(auto["users"], manual["users"]) >= 30 and pv is not None and pv < 0.05
        if sure:
            text = ("Сразу на балансе — лучше" if diff > 0 else "Сразу на балансе — хуже") + f": {diff:+.1f} п.п. (уверенность 95%)"
        else:
            text = f"Разница {diff:+.1f} п.п. пока не надёжна: в группах {auto['users']} и {manual['users']} человек"
        verdicts.append({"what": "Подключили VPN", "sure": sure, "verdict": text.replace(".", ",", 1)})
        verdicts.append({"what": "Оплатили", **compare(auto, manual, "manual")})
    return {"arms": items, "verdicts": verdicts}


async def overview() -> dict:
    tests = [dict(r) for r in await db._pool_req().fetch("SELECT * FROM auto_gift_tests ORDER BY id DESC LIMIT 10")]
    rows = await db._pool_req().fetch(RESULTS_SQL, [t["id"] for t in tests]) if tests else []
    by: dict[int, dict] = {t["id"]: {} for t in tests}
    for row in rows:
        by[int(row["test_id"])][row["arm"]] = dict(row)
    items = []
    for t in tests:
        items.append({"id": t["id"], "running": t["stopped_at"] is None,
                      "started_at": t["started_at"].astimezone(timezone.utc).isoformat(),
                      "stopped_at": t["stopped_at"].astimezone(timezone.utc).isoformat() if t["stopped_at"] else None,
                      **summarize(by[t["id"]])})
    return {"items": items, "window_days": WINDOW_DAYS, "auto_pct": AUTO_PCT}
