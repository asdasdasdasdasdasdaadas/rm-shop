"""A/B test of the cabinet's «install the app» step.

While a test runs, everyone who opens that step with no device yet is put in one group for good:
  old — as before: «Скачать» to the store, then a small ✓ «Уже стоит» that creates the key;
  new — two steps on one card: «Скачать» ticks step 1, «Добавить в …» creates the key and opens the app.
The cabinet learns the group from /api/me (install_ab) and records entry with the wizard_2 event.
The main measure is «подключили VPN за сутки»; keys made and payments within WINDOW_DAYS are shown too.
"""
from __future__ import annotations

from datetime import timezone

from app import db

WINDOW_DAYS = 7
ARMS = ("old", "new")
ARM_LABELS = {"old": "A · как сейчас", "new": "B · два шага на одной карточке"}
NEW_PCT = 50


async def running() -> dict | None:
    row = await db._pool_req().fetchrow("SELECT * FROM install_tests WHERE stopped_at IS NULL ORDER BY id DESC LIMIT 1")
    return dict(row) if row else None


async def start() -> int:
    if await running():
        raise ValueError("Тест уже идёт")
    return int(await db._pool_req().fetchval("INSERT INTO install_tests DEFAULT VALUES RETURNING id"))


async def stop() -> bool:
    return bool(await db._pool_req().fetchval(
        "UPDATE install_tests SET stopped_at=NOW() WHERE stopped_at IS NULL RETURNING id"))


def _arm(test_id: int, telegram_id: int) -> str:
    from app.experiments import bucket
    return "new" if bucket(int(test_id), int(telegram_id), "install") < NEW_PCT else "old"


async def arm_for(telegram_id: int, has_devices: bool) -> str | None:
    """The group the cabinet should show; None outside a test (the cabinet shows the usual step)."""
    test = await running()
    if not test:
        return None
    got = await db._pool_req().fetchval(
        "SELECT arm FROM install_arms WHERE test_id=$1 AND telegram_id=$2", int(test["id"]), int(telegram_id))
    if got:
        return str(got)
    return None if has_devices else _arm(test["id"], telegram_id)


async def enter(telegram_id: int) -> str | None:
    """Put the person in the test when they open the install step for their first device."""
    test = await running()
    if not test:
        return None
    pool = db._pool_req()
    has = await pool.fetchval("SELECT EXISTS (SELECT 1 FROM devices WHERE telegram_id=$1)", int(telegram_id))
    known = await pool.fetchval(
        "SELECT arm FROM install_arms WHERE test_id=$1 AND telegram_id=$2", int(test["id"]), int(telegram_id))
    if known or has:
        return known
    return await pool.fetchval(
        """INSERT INTO install_arms (test_id, telegram_id, arm) VALUES ($1, $2, $3)
           ON CONFLICT (test_id, telegram_id) DO UPDATE SET arm = install_arms.arm RETURNING arm""",
        int(test["id"]), int(telegram_id), _arm(test["id"], telegram_id))


RESULTS_SQL = f"""
WITH per_user AS (
    SELECT a.test_id, a.arm, a.telegram_id,
        a.assigned_at <= NOW() - INTERVAL '1 day' AS day_done,
        EXISTS (SELECT 1 FROM onboarding_events o WHERE o.telegram_id = a.telegram_id AND o.stage = 'wizard_4'
            AND o.created_at >= a.assigned_at AND o.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days')
          OR EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = a.telegram_id AND d.created_at >= a.assigned_at
            AND d.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS device,
        (u.first_online_at >= a.assigned_at AND u.first_online_at < a.assigned_at + INTERVAL '1 day') AS connected_day,
        (u.first_online_at >= a.assigned_at AND u.first_online_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS connected,
        (SELECT COUNT(*) FROM payment_receipts p WHERE p.telegram_id = a.telegram_id
            AND p.created_at >= a.assigned_at AND p.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS payments,
        (SELECT COALESCE(SUM(p.amount), 0) FROM payment_receipts p WHERE p.telegram_id = a.telegram_id
            AND p.created_at >= a.assigned_at AND p.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS rub
    FROM install_arms a JOIN users u ON u.telegram_id = a.telegram_id
    WHERE a.test_id = ANY($1::bigint[])
)
SELECT test_id, arm, COUNT(*)::int AS users,
    COUNT(*) FILTER (WHERE day_done)::int AS day_done,
    COUNT(*) FILTER (WHERE day_done AND connected_day)::int AS connected_day,
    COUNT(*) FILTER (WHERE device)::int AS device,
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
        text = ("Новый шаг лучше" if diff > 0 else "Новый шаг хуже") + f": {sign} п.п. (уверенность 95%)"
    else:
        text = f"Разница {sign} п.п. пока не надёжна: в группах {n1} и {n2} человек"
    return {"what": what, "sure": sure, "verdict": text}


def summarize(rows: dict[str, dict]) -> dict:
    from app.experiments import compare
    items = []
    for arm in ARMS:
        data = {k: int(v) for k, v in (rows.get(arm) or {}).items() if k not in {"test_id", "arm"}}
        for key in ("users", "day_done", "connected_day", "device", "connected", "payers", "rub"):
            data.setdefault(key, 0)
        n = data["users"]
        data.update(arm=arm, label=ARM_LABELS[arm], device_pct=_pct(data["device"], n),
                    connected_day_pct=_pct(data["connected_day"], data["day_done"]),
                    connected_pct=_pct(data["connected"], n), conversion=_pct(data["payers"], n),
                    rub_per_user=round(data["rub"] / n, 1) if n else 0.0)
        items.append(data)
    old, new = items
    verdicts = []
    if old["users"] and new["users"]:
        verdicts.append(_verdict("Подключили VPN за сутки", new["connected_day"], new["day_done"],
                                 old["connected_day"], old["day_done"]))
        verdicts.append(_verdict("Создали ключ", new["device"], new["users"], old["device"], old["users"]))
        pay = compare(new, old, "old")
        verdicts.append({"what": "Оплатили", "sure": pay["sure"], "verdict": pay["verdict"]})
    return {"arms": items, "verdicts": verdicts}


async def overview() -> dict:
    tests = [dict(r) for r in await db._pool_req().fetch("SELECT * FROM install_tests ORDER BY id DESC LIMIT 10")]
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
    return {"items": items, "window_days": WINDOW_DAYS, "new_pct": NEW_PCT}
