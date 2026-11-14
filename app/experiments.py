"""A/B tests for the bot's automatic messages.

One test per step of a built-in journey. Everyone who is due the step is put in one arm, for good:
  a       — the usual text and gift;
  b       — another text and/or another number of gift days;
  control — nothing is sent; the journey moves on as if the step went out.
The control group answers «does this message bring money at all»; A against B answers «which one brings more».
Results count every payment within WINDOW_DAYS after a person entered the test, whether they clicked or not.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone

from app import db

ARMS = ("a", "b", "control")
WINDOW_DAYS = 7
MAX_HOLDOUT = 50
# Below this the z-test is not trusted, whatever it says.
MIN_USERS, MIN_PAYERS = 30, 10
GIFT_DAYS_RANGE = (1, 14)
ARM_LABELS = {"a": "A · как сейчас", "b": "B · новый вариант", "control": "Контроль · без сообщения"}


def bucket(experiment_id: int, telegram_id: int, salt: str = "") -> float:
    """A stable number from 0 to 100 for this person in this test."""
    digest = hashlib.sha256(f"{experiment_id}:{int(telegram_id)}:{salt}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % 10000 / 100


def arm_for(exp: dict, telegram_id: int) -> str:
    holdout = int(exp.get("holdout_pct") or 0)
    if holdout and bucket(exp["id"], telegram_id, "holdout") < holdout:
        return "control"
    b_pct = int(exp.get("b_pct") or 0)
    return "b" if b_pct and bucket(exp["id"], telegram_id, "split") < b_pct else "a"


async def running() -> dict[str, dict]:
    """Running tests by step id."""
    rows = await db._pool_req().fetch("SELECT * FROM funnel_experiments WHERE stopped_at IS NULL")
    return {row["step_id"]: dict(row) for row in rows}


async def assign(exp: dict, telegram_id: int) -> str:
    """The person's arm. The first assignment sticks, so a later retry or a new cycle keeps the same arm."""
    arm = arm_for(exp, telegram_id)
    got = await db._pool_req().fetchval(
        """INSERT INTO funnel_experiment_users (experiment_id, telegram_id, arm)
           VALUES ($1, $2, $3)
           ON CONFLICT (experiment_id, telegram_id) DO UPDATE SET arm = funnel_experiment_users.arm
           RETURNING arm""",
        int(exp["id"]), int(telegram_id), arm)
    return str(got or arm)


async def mark_delivered(exp: dict, telegram_id: int) -> None:
    await db._pool_req().execute(
        """UPDATE funnel_experiment_users SET delivered_at = COALESCE(delivered_at, NOW())
           WHERE experiment_id = $1 AND telegram_id = $2""", int(exp["id"]), int(telegram_id))


def variant(step: dict, exp: dict | None, arm: str) -> tuple[str, int | None]:
    """The text and the gift days (None = usual) this arm gets."""
    if not exp or arm != "b":
        return step["text"], None
    text = str(exp.get("b_text") or "").strip() or step["text"]
    days = exp.get("b_gift_days")
    return text, int(days) if days else None


# ---------- admin ----------

def testable_steps(graph: dict) -> list[dict]:
    from app.funnel_board import CONDITION_IDS, GIFT_ACTION
    steps = []
    for branch in graph.get("branches") or []:
        for n, step in enumerate(branch["steps"], 1):
            spec = CONDITION_IDS.get(step["condition"]) or {}
            if spec.get("special") or not step.get("enabled", True):
                continue  # unpaid invoice and balance warnings are about money already in play: never held back
            actions = {b if isinstance(b, str) else b.get("action") for b in step["buttons"]}
            steps.append({
                "id": step["id"], "branch": branch["title"], "n": n, "condition": spec.get("label") or step["condition"],
                "wait_hours": step["wait_hours"], "text": step["text"], "gift": GIFT_ACTION in actions,
            })
    return steps


def check(body: dict, steps: dict[str, dict]) -> dict:
    step_id = str(body.get("step_id") or "")
    step = steps.get(step_id)
    if not step:
        raise ValueError("Выберите сообщение из списка")

    def whole(key, lo, hi, label):
        raw = body.get(key)
        if raw in (None, ""):
            return 0
        if isinstance(raw, bool) or not str(raw).strip().isdigit() or not lo <= int(raw) <= hi:
            raise ValueError(f"{label}: целое число от {lo} до {hi}")
        return int(raw)

    holdout = whole("holdout_pct", 0, MAX_HOLDOUT, "Контрольная группа")
    b_pct = whole("b_pct", 0, 100, "Доля варианта B")
    text = str(body.get("b_text") or "").strip()
    if len(text) > 3500:
        raise ValueError("Текст варианта B — до 3500 символов")
    days = body.get("b_gift_days")
    days = whole("b_gift_days", *GIFT_DAYS_RANGE, "Дней в подарке") if days not in (None, "") else None
    if days and not step["gift"]:
        raise ValueError("В этом сообщении нет подарка — менять дни не на чем")
    if text:
        from app.funnel_board import render_text
        try:
            render_text(text, 1, "Имя")
        except Exception:
            raise ValueError("Текст варианта B не читается")
        if text == step["text"].strip() and not days:
            raise ValueError("Вариант B совпадает с A")
    if b_pct and not text and not days:
        raise ValueError("Для варианта B напишите текст или измените подарок")
    if not b_pct and (text or days):
        raise ValueError("Укажите, какой доле отправлять вариант B")
    if not holdout and not b_pct:
        raise ValueError("Нечего сравнивать: задайте контрольную группу или вариант B")
    if b_pct == 100 and not holdout:
        pass  # «оставить B для всех»: B replaces A until stopped
    return {"step_id": step_id, "holdout_pct": holdout, "b_pct": b_pct,
            "b_text": text or None, "b_gift_days": days, "note": str(body.get("note") or "").strip()[:200] or None}


async def create(clean: dict) -> int:
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            busy = await conn.fetchval(
                "SELECT id FROM funnel_experiments WHERE step_id=$1 AND stopped_at IS NULL FOR UPDATE", clean["step_id"])
            if busy:
                raise ValueError("Для этого сообщения тест уже идёт — сначала остановите его")
            return int(await conn.fetchval(
                """INSERT INTO funnel_experiments (step_id, holdout_pct, b_pct, b_text, b_gift_days, note)
                   VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
                clean["step_id"], clean["holdout_pct"], clean["b_pct"], clean["b_text"], clean["b_gift_days"], clean["note"]))


async def stop(experiment_id: int) -> bool:
    return bool(await db._pool_req().fetchval(
        "UPDATE funnel_experiments SET stopped_at=NOW() WHERE id=$1 AND stopped_at IS NULL RETURNING id",
        int(experiment_id)))


RESULTS_SQL = f"""
WITH members AS (
    SELECT e.experiment_id, e.telegram_id, e.arm, e.assigned_at, e.delivered_at, x.step_id
    FROM funnel_experiment_users e JOIN funnel_experiments x ON x.id = e.experiment_id
    WHERE e.experiment_id = ANY($1::bigint[])
), per_user AS (
    SELECT m.experiment_id, m.arm, m.telegram_id, m.delivered_at,
        m.assigned_at <= NOW() - INTERVAL '{WINDOW_DAYS} days' AS matured,
        COALESCE(SUM(p.amount), 0) AS rub,
        COUNT(p.payment_key) AS payments,
        BOOL_OR(p.first_payment) AS first_paid,
        (SELECT u.first_online_at >= m.assigned_at AND u.first_online_at < m.assigned_at + INTERVAL '{WINDOW_DAYS} days'
           FROM users u WHERE u.telegram_id = m.telegram_id) AS connected,
        EXISTS (SELECT 1 FROM reminder_deliveries r WHERE r.telegram_id = m.telegram_id AND r.step_id = m.step_id
            AND r.created_at >= m.assigned_at AND r.clicked_at IS NOT NULL) AS clicked,
        (SELECT COALESCE(SUM(g.gift_rub), 0) FROM funnel_gifts g WHERE g.telegram_id = m.telegram_id
            AND g.step_id = m.step_id AND g.created_at >= m.assigned_at AND g.claimed_at IS NOT NULL) AS gift_rub
    FROM members m
    LEFT JOIN payment_receipts p ON p.telegram_id = m.telegram_id
        AND p.created_at >= m.assigned_at AND p.created_at < m.assigned_at + INTERVAL '{WINDOW_DAYS} days'
    GROUP BY m.experiment_id, m.arm, m.telegram_id, m.delivered_at, m.assigned_at, m.step_id
)
SELECT experiment_id, arm,
    COUNT(*)::int AS users,
    COUNT(*) FILTER (WHERE matured)::int AS matured,
    COUNT(delivered_at)::int AS delivered,
    COUNT(*) FILTER (WHERE clicked)::int AS clicked,
    COUNT(*) FILTER (WHERE connected)::int AS connected,
    COUNT(*) FILTER (WHERE payments > 0)::int AS payers,
    COUNT(*) FILTER (WHERE first_paid)::int AS first_payers,
    COALESCE(SUM(payments), 0)::int AS payments,
    COALESCE(SUM(rub), 0)::bigint AS rub,
    COALESCE(SUM(gift_rub), 0)::bigint AS gift_rub
FROM per_user GROUP BY experiment_id, arm
"""


def p_value(x1: int, n1: int, x2: int, n2: int) -> float | None:
    """Two-sided two-proportion z-test. None when there is too little to say anything."""
    if min(n1, n2) < 1:
        return None
    pooled = (x1 + x2) / (n1 + n2)
    if pooled in (0, 1):
        return 1.0
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = abs(x1 / n1 - x2 / n2) / se
    return math.erfc(z / math.sqrt(2))


def needed_per_arm(p: float, lift: float = 0.3) -> int:
    """People per arm to notice a relative change of `lift` in a conversion of `p` (95%, power 80%)."""
    p = min(max(p, 0.01), 0.9)
    q = p * (1 + lift)
    var = p * (1 - p) + q * (1 - q)
    return int(math.ceil((1.96 + 0.84) ** 2 * var / (q - p) ** 2))


def compare(arm: dict, base: dict, base_name: str) -> dict:
    """Payers and money of one arm against another, per 100 people, with a plain verdict."""
    n1, n2 = arm["users"], base["users"]
    if not n1 or not n2:
        return {"against": base_name, "verdict": "Пока нет людей в обеих группах", "sure": False}
    c1, c2 = arm["payers"] / n1, base["payers"] / n2
    rub1, rub2 = arm["rub"] / n1, base["rub"] / n2
    pv = p_value(arm["payers"], n1, base["payers"], n2)
    enough = min(n1, n2) >= MIN_USERS and arm["payers"] + base["payers"] >= MIN_PAYERS
    sure = enough and pv is not None and pv < 0.05
    diff_pp = (c1 - c2) * 100
    if sure:
        verdict = ("Лучше" if c1 > c2 else "Хуже") + f": {diff_pp:+.1f}".replace(".", ",") + " п.п. к доле оплативших (уверенность 95%)"
    else:
        need = max(MIN_USERS, needed_per_arm(max(c2, c1, 0.02)))
        verdict = (f"Разница пока не надёжна: в каждой группе нужно хотя бы {need}, сейчас {min(n1, n2)}"
                   if min(n1, n2) < need else "Разницы не видно: варианты работают примерно одинаково")
    return {"against": base_name, "payers_pp": round(diff_pp, 2), "rub_per_100": round((rub1 - rub2) * 100),
            "p_value": None if pv is None else round(pv, 4), "sure": sure, "verdict": verdict}


async def results(experiment_ids: list[int]) -> dict[int, dict]:
    rows = await db._pool_req().fetch(RESULTS_SQL, [int(i) for i in experiment_ids]) if experiment_ids else []
    out: dict[int, dict] = {int(i): {} for i in experiment_ids}
    for row in rows:
        out[int(row["experiment_id"])][row["arm"]] = dict(row)
    return {exp_id: summarize(arms) for exp_id, arms in out.items()}


def summarize(arms: dict[str, dict]) -> dict:
    """Arms as rows with conversion and ₽ per person, and the comparisons that can be made."""
    items = []
    for arm in ARMS:
        data = arms.get(arm) or {"users": 0, "matured": 0, "delivered": 0, "clicked": 0, "connected": 0,
                                 "payers": 0, "first_payers": 0, "payments": 0, "rub": 0, "gift_rub": 0}
        data = {k: int(v) for k, v in data.items() if k not in {"experiment_id", "arm"}}
        n = data["users"]
        data.update(arm=arm, label=ARM_LABELS[arm],
                    conversion=round(data["payers"] / n * 100, 1) if n else 0.0,
                    rub_per_user=round(data["rub"] / n, 1) if n else 0.0)
        items.append(data)
    by = {i["arm"]: i for i in items}
    comparisons = []
    if by["control"]["users"]:
        for arm in ("a", "b"):
            if by[arm]["users"]:
                comparisons.append({"arm": arm, **compare(by[arm], by["control"], "control")})
    if by["a"]["users"] and by["b"]["users"]:
        comparisons.append({"arm": "b", **compare(by["b"], by["a"], "a")})
    return {"arms": [i for i in items if i["users"] or i["arm"] != "b"], "comparisons": comparisons}


async def overview(graph: dict) -> dict:
    steps = testable_steps(graph)
    rows = await db._pool_req().fetch("SELECT * FROM funnel_experiments ORDER BY id DESC LIMIT 50")
    found = await results([int(r["id"]) for r in rows])
    by_step = {s["id"]: s for s in steps}
    items = []
    for row in rows:
        item = {k: (v.astimezone(timezone.utc).isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()}
        step = by_step.get(row["step_id"])
        item.update(step=step, running=row["stopped_at"] is None, **found.get(int(row["id"]), {}))
        items.append(item)
    return {"steps": steps, "items": items, "window_days": WINDOW_DAYS, "max_holdout": MAX_HOLDOUT}


# ---------- manual broadcasts ----------

def broadcast_arm(run_id: int, telegram_id: int, holdout: int, with_b: bool) -> str:
    """Half of those who are not in control get B, when there is a B."""
    return arm_for({"id": f"bc{int(run_id)}", "holdout_pct": holdout, "b_pct": 50 if with_b else 0}, telegram_id)


async def assign_broadcast(run_id: int, telegram_id: int, arm: str) -> None:
    await db._pool_req().execute(
        """INSERT INTO broadcast_arms (run_id, telegram_id, arm) VALUES ($1, $2, $3)
           ON CONFLICT (run_id, telegram_id) DO NOTHING""", int(run_id), int(telegram_id), arm)


async def broadcast_delivered(run_id: int, telegram_id: int) -> None:
    await db._pool_req().execute(
        "UPDATE broadcast_arms SET delivered_at=COALESCE(delivered_at, NOW()) WHERE run_id=$1 AND telegram_id=$2",
        int(run_id), int(telegram_id))


BROADCAST_RESULTS_SQL = f"""
WITH per_user AS (
    SELECT m.run_id, m.arm, m.telegram_id, m.delivered_at,
        COALESCE(SUM(p.amount), 0) AS rub,
        COUNT(p.payment_key) AS payments,
        BOOL_OR(p.first_payment) AS first_paid,
        (SELECT u.first_online_at >= m.assigned_at AND u.first_online_at < m.assigned_at + INTERVAL '{WINDOW_DAYS} days'
           FROM users u WHERE u.telegram_id = m.telegram_id) AS connected,
        EXISTS (SELECT 1 FROM reminder_deliveries r WHERE r.telegram_id = m.telegram_id AND r.broadcast_id = m.run_id
            AND r.clicked_at IS NOT NULL) AS clicked
    FROM broadcast_arms m
    LEFT JOIN payment_receipts p ON p.telegram_id = m.telegram_id
        AND p.created_at >= m.assigned_at AND p.created_at < m.assigned_at + INTERVAL '{WINDOW_DAYS} days'
    WHERE m.run_id = ANY($1::bigint[])
    GROUP BY m.run_id, m.arm, m.telegram_id, m.delivered_at, m.assigned_at
)
SELECT run_id, arm, COUNT(*)::int AS users, 0 AS matured,
    COUNT(delivered_at)::int AS delivered,
    COUNT(*) FILTER (WHERE clicked)::int AS clicked,
    COUNT(*) FILTER (WHERE connected)::int AS connected,
    COUNT(*) FILTER (WHERE payments > 0)::int AS payers,
    COUNT(*) FILTER (WHERE first_paid)::int AS first_payers,
    COALESCE(SUM(payments), 0)::int AS payments,
    COALESCE(SUM(rub), 0)::bigint AS rub,
    0::bigint AS gift_rub
FROM per_user GROUP BY run_id, arm
"""


async def broadcast_results(run_ids: list[int]) -> dict[int, dict]:
    if not run_ids:
        return {}
    rows = await db._pool_req().fetch(BROADCAST_RESULTS_SQL, [int(i) for i in run_ids])
    found: dict[int, dict] = {}
    for row in rows:
        data = dict(row)
        found.setdefault(int(data.pop("run_id")), {})[row["arm"]] = data
    return {run_id: summarize(arms) for run_id, arms in found.items()}
