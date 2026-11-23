"""The living frog on the cabinet's home card (webapp/frog.js): on/off and its A/B test.

Outside a test everyone sees the frog: it is the default home card.
People listed in «Кому показывать всегда» (frog_user_ids: IDs and @usernames) see it in any case and stay out of the test.
While a test runs, everyone who opens the cabinet is put in one group for good:
  frog  — the home card with the living frog;
  plain — the home card as before, with the still frog picture.
The question is whether the frog pulls people in, leaves them cold, or puts them off:
  pull       — they come back to the cabinet on another day more often (the main measure);
  money      — they press «Пополнить» on the home card and pay no less (the guard: a cute toy must not cost money);
  interest   — how many play with the frog at all, and how many play again and again (frog group only).
«Пофиг» is no difference and few players; «оттолкнуло» is fewer returns or fewer top-ups with confidence.
"""
from __future__ import annotations

from datetime import timezone

from app import db
from app.config import get_settings

ARMS = ("plain", "frog")
ARM_LABELS = {"plain": "A · без лягушки", "frog": "B · живая лягушка"}
FROG_PCT = 50
RETURN_DAYS = 3      # «вернулись»: opened the cabinet again on another day within this many days
WINDOW_DAYS = 7      # money and active days are counted over this window
FAN_PLAYS = 5        # played this many times or more: a fan
KINDS = {"open": "opens", "play": "plays", "topup": "topups"}
_DAY = "(NOW() AT TIME ZONE 'Europe/Moscow')::date"


async def running() -> dict | None:
    row = await db._pool_req().fetchrow("SELECT * FROM frog_tests WHERE stopped_at IS NULL ORDER BY id DESC LIMIT 1")
    return dict(row) if row else None


async def start() -> int:
    if await running():
        raise ValueError("Тест уже идёт")
    return int(await db._pool_req().fetchval("INSERT INTO frog_tests DEFAULT VALUES RETURNING id"))


async def stop() -> bool:
    return bool(await db._pool_req().fetchval(
        "UPDATE frog_tests SET stopped_at=NOW() WHERE stopped_at IS NULL RETURNING id"))


def _arm(test_id: int, telegram_id: int) -> str:
    from app.experiments import bucket
    return "frog" if bucket(int(test_id), int(telegram_id), "frog") < FROG_PCT else "plain"


def _listed_people() -> tuple[set[int], set[str]]:
    ids, names = set(), set()
    for token in str(get_settings().frog_user_ids or "").replace(",", " ").split():
        if token.isdigit():
            ids.add(int(token))
        elif token.startswith("@") and len(token) > 1:
            names.add(token[1:].lower())
    return ids, names


async def listed(telegram_id: int) -> bool:
    """On the owner's «always show» list, by ID or by the @username the bot knows."""
    ids, names = _listed_people()
    if int(telegram_id) in ids:
        return True
    if not names:
        return False
    username = await db._pool_req().fetchval("SELECT username FROM users WHERE telegram_id=$1", int(telegram_id))
    return bool(username) and str(username).lstrip("@").lower() in names


async def view(telegram_id: int) -> dict:
    """What the cabinet shows: {"on": bool, "ab": arm or None}. Opening the cabinet during a test puts the person in it."""
    if await listed(telegram_id):
        return {"on": True, "ab": None}
    test = await running()
    if test:
        arm = await db._pool_req().fetchval(
            """INSERT INTO frog_arms (test_id, telegram_id, arm) VALUES ($1, $2, $3)
               ON CONFLICT (test_id, telegram_id) DO UPDATE SET arm = frog_arms.arm RETURNING arm""",
            int(test["id"]), int(telegram_id), _arm(test["id"], telegram_id))
        return {"on": arm == "frog", "ab": str(arm)}
    return {"on": True, "ab": None}


async def record(telegram_id: int, kind: str) -> bool:
    """One event of a person in the running test, added to today's row. Outside a test nothing is kept."""
    col = KINDS.get(kind)
    if not col:
        raise ValueError("Некорректное событие")
    return bool(await db._pool_req().fetchval(
        f"""INSERT INTO frog_days (test_id, telegram_id, day, {col})
            SELECT a.test_id, a.telegram_id, {_DAY}, 1
            FROM frog_arms a JOIN frog_tests t ON t.id = a.test_id AND t.stopped_at IS NULL
            WHERE a.telegram_id = $1
            ON CONFLICT (test_id, telegram_id, day) DO UPDATE SET {col} = frog_days.{col} + 1
            RETURNING 1""", int(telegram_id)))


RESULTS_SQL = f"""
WITH per_user AS (
    SELECT a.test_id, a.arm, a.telegram_id,
        a.assigned_at <= NOW() - INTERVAL '{RETURN_DAYS} days' AS ret_done,
        EXISTS (SELECT 1 FROM frog_days d WHERE d.test_id = a.test_id AND d.telegram_id = a.telegram_id AND d.opens > 0
            AND d.day > (a.assigned_at AT TIME ZONE 'Europe/Moscow')::date
            AND d.day <= (a.assigned_at AT TIME ZONE 'Europe/Moscow')::date + {RETURN_DAYS}) AS returned,
        (SELECT COUNT(*) FROM frog_days d WHERE d.test_id = a.test_id AND d.telegram_id = a.telegram_id AND d.opens > 0
            AND d.day < (a.assigned_at AT TIME ZONE 'Europe/Moscow')::date + {WINDOW_DAYS}) AS active_days,
        (SELECT COALESCE(SUM(d.plays), 0) FROM frog_days d WHERE d.test_id = a.test_id AND d.telegram_id = a.telegram_id) AS plays,
        (SELECT COALESCE(SUM(d.topups), 0) FROM frog_days d WHERE d.test_id = a.test_id AND d.telegram_id = a.telegram_id
            AND d.day < (a.assigned_at AT TIME ZONE 'Europe/Moscow')::date + {WINDOW_DAYS}) AS topups,
        (SELECT COUNT(*) FROM payment_receipts p WHERE p.telegram_id = a.telegram_id
            AND p.created_at >= a.assigned_at AND p.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS payments,
        (SELECT COALESCE(SUM(p.amount), 0) FROM payment_receipts p WHERE p.telegram_id = a.telegram_id
            AND p.created_at >= a.assigned_at AND p.created_at < a.assigned_at + INTERVAL '{WINDOW_DAYS} days') AS rub
    FROM frog_arms a
    WHERE a.test_id = ANY($1::bigint[])
)
SELECT test_id, arm, COUNT(*)::int AS users,
    COUNT(*) FILTER (WHERE ret_done)::int AS ret_done,
    COUNT(*) FILTER (WHERE ret_done AND returned)::int AS returned,
    COALESCE(SUM(active_days), 0)::int AS active_days,
    COUNT(*) FILTER (WHERE plays > 0)::int AS players,
    COUNT(*) FILTER (WHERE plays >= {FAN_PLAYS})::int AS fans,
    COALESCE(SUM(plays), 0)::int AS plays,
    COUNT(*) FILTER (WHERE topups > 0)::int AS topup_clickers,
    COUNT(*) FILTER (WHERE payments > 0)::int AS payers,
    COALESCE(SUM(rub), 0)::bigint AS rub
FROM per_user GROUP BY test_id, arm
"""


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def _diff(what: str, x1: int, n1: int, x2: int, n2: int) -> dict:
    """Frog (x1/n1) against plain (x2/n2): the difference in points and whether it can be trusted."""
    from app.experiments import MIN_USERS, p_value
    if not n1 or not n2:
        return {"what": what, "sure": False, "up": None, "verdict": "Пока нет людей в обеих группах"}
    diff = (x1 / n1 - x2 / n2) * 100
    pv = p_value(x1, n1, x2, n2)
    sure = min(n1, n2) >= MIN_USERS and pv is not None and pv < 0.05
    sign = f"{diff:+.1f}".replace(".", ",")
    if sure:
        text = ("С лягушкой больше" if diff > 0 else "С лягушкой меньше") + f": {sign} п.п. (уверенность 95%)"
    else:
        text = f"Разница {sign} п.п. пока не надёжна: в группах {n1} и {n2} человек"
    return {"what": what, "sure": sure, "up": diff > 0, "verdict": text}


def _bottom_line(ret: dict, top: dict, pay: dict, frog: dict, plain: dict) -> dict:
    """One line for the owner: pulls, puts off, leaves cold, or too early to say."""
    from app.experiments import MIN_USERS
    if (ret["sure"] and not ret["up"]) or (top["sure"] and not top["up"]) or (pay["sure"] and not pay["up"]):
        why = "реже возвращаются" if ret["sure"] and not ret["up"] else "реже пополняют"
        return {"what": "Итог", "sure": True, "verdict": f"Отталкивает: с лягушкой {why}. Лучше выключить."}
    if ret["sure"] and ret["up"]:
        return {"what": "Итог", "sure": True,
                "verdict": "Притягивает: с лягушкой чаще возвращаются в кабинет, деньги не страдают. Можно включать всем."}
    enough = min(frog["ret_done"], plain["ret_done"]) >= MIN_USERS
    if enough and frog["play_pct"] < 15:
        return {"what": "Итог", "sure": False,
                "verdict": f"Похоже, пофиг: играют {frog['play_pct']:g}%, разницы в возвратах и деньгах не видно."}
    if enough and frog["fan_pct"] >= 10:
        return {"what": "Итог", "sure": False,
                "verdict": f"Нравится части людей: {frog['fan_pct']:g}% играют снова и снова, но на возвраты это пока не влияет."}
    return {"what": "Итог", "sure": False, "verdict": "Пока рано: нужно больше людей, проживших в тесте хотя бы 3 дня."}


def summarize(rows: dict[str, dict]) -> dict:
    from app.experiments import compare
    items = []
    for arm in ARMS:
        data = {k: int(v) for k, v in (rows.get(arm) or {}).items() if k not in {"test_id", "arm"}}
        for key in ("users", "ret_done", "returned", "active_days", "players", "fans", "plays", "topup_clickers", "payers", "rub"):
            data.setdefault(key, 0)
        n = data["users"]
        data.update(arm=arm, label=ARM_LABELS[arm], return_pct=_pct(data["returned"], data["ret_done"]),
                    days_per_user=round(data["active_days"] / n, 2) if n else 0.0,
                    play_pct=_pct(data["players"], n), fan_pct=_pct(data["fans"], n),
                    topup_pct=_pct(data["topup_clickers"], n), conversion=_pct(data["payers"], n),
                    rub_per_user=round(data["rub"] / n, 1) if n else 0.0)
        items.append(data)
    plain, frog = items
    verdicts = []
    if plain["users"] and frog["users"]:
        ret = _diff(f"Вернулись в кабинет за {RETURN_DAYS} дня", frog["returned"], frog["ret_done"], plain["returned"], plain["ret_done"])
        top = _diff("Нажали «Пополнить» на главной", frog["topup_clickers"], frog["users"], plain["topup_clickers"], plain["users"])
        money = compare(frog, plain, "plain")
        pay = {"what": "Оплатили", "sure": money["sure"], "up": (money.get("payers_pp") or 0) > 0, "verdict": money["verdict"]}
        verdicts = [_bottom_line(ret, top, pay, frog, plain), ret, top, pay]
    return {"arms": items, "verdicts": [{k: v for k, v in x.items() if k != "up"} for x in verdicts]}


async def overview() -> dict:
    tests = [dict(r) for r in await db._pool_req().fetch("SELECT * FROM frog_tests ORDER BY id DESC LIMIT 10")]
    rows = await db._pool_req().fetch(RESULTS_SQL, [t["id"] for t in tests]) if tests else []
    by: dict[int, dict] = {t["id"]: {} for t in tests}
    for row in rows:
        by[int(row["test_id"])][row["arm"]] = dict(row)

    def iso(v):
        if v is None or isinstance(v, str):
            return v
        return v.astimezone(timezone.utc).isoformat()

    items = [{"id": t["id"], "running": t["stopped_at"] is None, "started_at": iso(t["started_at"]),
              "stopped_at": iso(t["stopped_at"]), **summarize(by[t["id"]])} for t in tests]
    return {"items": items, "window_days": WINDOW_DAYS, "return_days": RETURN_DAYS, "frog_pct": FROG_PCT}
