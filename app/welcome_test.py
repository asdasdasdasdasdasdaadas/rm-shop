"""A/B test of the first message after /start.

While a test runs, every newcomer who gets the welcome is put in one group for good:
  plain — as before: a sticker, then the hello with the gift and one button;
  card  — one card: the banner (app/assets/welcome-card.jpg), what the VPN gives as a short list, and
          «Подключить за минуту». The gift, the button's target and the legal line are the same.
The main measure is «подключили VPN за сутки»; the gift, the key and payments within WINDOW_DAYS are shown too.
"""
from __future__ import annotations

from datetime import timezone

from app import db

WINDOW_DAYS = 7
ARMS = ("plain", "card")
ARM_LABELS = {"plain": "A · стикер и текст", "card": "B · карточка с баннером"}
CARD_PCT = 50


async def running() -> dict | None:
    row = await db._pool_req().fetchrow("SELECT * FROM welcome_tests WHERE stopped_at IS NULL ORDER BY id DESC LIMIT 1")
    return dict(row) if row else None


async def start() -> int:
    if await running():
        raise ValueError("Тест уже идёт")
    return int(await db._pool_req().fetchval("INSERT INTO welcome_tests DEFAULT VALUES RETURNING id"))


async def stop() -> bool:
    return bool(await db._pool_req().fetchval(
        "UPDATE welcome_tests SET stopped_at=NOW() WHERE stopped_at IS NULL RETURNING id"))


def _arm(test_id: int, telegram_id: int) -> str:
    from app.experiments import bucket
    return "card" if bucket(int(test_id), int(telegram_id), "welcome") < CARD_PCT else "plain"


async def enter(telegram_id: int) -> str | None:
    """The group for a newcomer's welcome; None outside a test (the usual welcome)."""
    test = await running()
    if not test:
        return None
    return str(await db._pool_req().fetchval(
        """INSERT INTO welcome_arms (test_id, telegram_id, arm) VALUES ($1, $2, $3)
           ON CONFLICT (test_id, telegram_id) DO UPDATE SET arm = welcome_arms.arm RETURNING arm""",
        int(test["id"]), int(telegram_id), _arm(test["id"], telegram_id)))


RESULTS_SQL = f"""
WITH per_user AS (
    SELECT a.test_id, a.arm, a.telegram_id,
        a.assigned_at <= NOW() - INTERVAL '1 day' AS day_done,
        COALESCE(u.trial_used, FALSE) AS gift,
        EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = a.telegram_id AND d.created_at >= a.assigned_at
            AND d.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS device,
        (u.first_online_at >= a.assigned_at AND u.first_online_at < a.assigned_at + INTERVAL '1 day') AS connected_day,
        (u.first_online_at >= a.assigned_at AND u.first_online_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS connected,
        (SELECT COUNT(*) FROM payment_receipts p WHERE p.telegram_id = a.telegram_id
            AND p.created_at >= a.assigned_at AND p.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS payments,
        (SELECT COALESCE(SUM(p.amount), 0) FROM payment_receipts p WHERE p.telegram_id = a.telegram_id
            AND p.created_at >= a.assigned_at AND p.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS rub
    FROM welcome_arms a JOIN users u ON u.telegram_id = a.telegram_id
    WHERE a.test_id = ANY($1::bigint[])
)
SELECT test_id, arm, COUNT(*)::int AS users,
    COUNT(*) FILTER (WHERE day_done)::int AS day_done,
    COUNT(*) FILTER (WHERE gift)::int AS gift,
    COUNT(*) FILTER (WHERE device)::int AS device,
    COUNT(*) FILTER (WHERE day_done AND connected_day)::int AS connected_day,
    COUNT(*) FILTER (WHERE connected)::int AS connected,
    COUNT(*) FILTER (WHERE payments > 0)::int AS payers,
    COALESCE(SUM(rub), 0)::bigint AS rub
FROM per_user GROUP BY test_id, arm
"""


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def _verdict(what: str, x1: int, n1: int, x2: int, n2: int) -> dict:
    from app.experiments import MIN_USERS, p_value
    if not n1 or not n2:
        return {"what": what, "sure": False, "verdict": "Пока нет людей в обеих группах"}
    diff = (x1 / n1 - x2 / n2) * 100
    pv = p_value(x1, n1, x2, n2)
    sure = min(n1, n2) >= MIN_USERS and pv is not None and pv < 0.05
    sign = f"{diff:+.1f}".replace(".", ",")
    if sure:
        text = ("Карточка лучше" if diff > 0 else "Карточка хуже") + f": {sign} п.п. (уверенность 95%)"
    else:
        text = f"Разница {sign} п.п. пока не надёжна: в группах {n1} и {n2} человек"
    return {"what": what, "sure": sure, "verdict": text}


def summarize(rows: dict[str, dict]) -> dict:
    from app.experiments import compare
    items = []
    for arm in ARMS:
        data = {k: int(v) for k, v in (rows.get(arm) or {}).items() if k not in {"test_id", "arm"}}
        for key in ("users", "day_done", "gift", "device", "connected_day", "connected", "payers", "rub"):
            data.setdefault(key, 0)
        n = data["users"]
        data.update(arm=arm, label=ARM_LABELS[arm], gift_pct=_pct(data["gift"], n), device_pct=_pct(data["device"], n),
                    connected_day_pct=_pct(data["connected_day"], data["day_done"]),
                    connected_pct=_pct(data["connected"], n), conversion=_pct(data["payers"], n),
                    rub_per_user=round(data["rub"] / n, 1) if n else 0.0)
        items.append(data)
    plain, card = items
    verdicts = []
    if plain["users"] and card["users"]:
        verdicts.append(_verdict("Подключили VPN за сутки", card["connected_day"], card["day_done"],
                                 plain["connected_day"], plain["day_done"]))
        verdicts.append(_verdict("Создали ключ", card["device"], card["users"], plain["device"], plain["users"]))
        pay = compare(card, plain, "plain")
        verdicts.append({"what": "Оплатили", "sure": pay["sure"], "verdict": pay["verdict"]})
    return {"arms": items, "verdicts": verdicts}


async def overview() -> dict:
    tests = [dict(r) for r in await db._pool_req().fetch("SELECT * FROM welcome_tests ORDER BY id DESC LIMIT 10")]
    rows = await db._pool_req().fetch(RESULTS_SQL, [t["id"] for t in tests]) if tests else []
    by: dict[int, dict] = {t["id"]: {} for t in tests}
    for row in rows:
        by[int(row["test_id"])][row["arm"]] = dict(row)

    def iso(v):
        if v is None:
            return None
        if isinstance(v, str):
            return v
        return v.astimezone(timezone.utc).isoformat()

    items = [{"id": t["id"], "running": t["stopped_at"] is None, "started_at": iso(t["started_at"]),
              "stopped_at": iso(t["stopped_at"]), **summarize(by[t["id"]])} for t in tests]
    return {"items": items, "window_days": WINDOW_DAYS, "card_pct": CARD_PCT}
