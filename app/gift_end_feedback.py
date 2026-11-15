"""«Почему не продолжили?» — one question when free access ran out and the person never paid.

Asked once by the funnel step recovery-recover-why-1. Each answer also does what the matching
«Нужна помощь» / «Не подошли условия» / «Пока не нужен» buttons do, so support and later offers react to it.
"""
from app import db

ACTIONS = {"why_price": "price", "why_broken": "broken", "why_payment": "payment", "why_later": "later"}
REASONS = {"price": "Дорого", "broken": "VPN работал плохо", "payment": "Неудобно оплатить", "later": "Пока не нужен"}
# The matching answer of the older feedback buttons: «Дорого» gets the «условия не подошли» gift offer,
# «работал плохо» goes to support, «пока не нужен» stops the comeback reminders.
AS_VPN_FEEDBACK = {"price": "terms", "broken": "help", "later": "later"}


async def save(telegram_id: int, reason: str) -> bool:
    if reason not in REASONS:
        return False
    await db._pool_req().execute(
        """INSERT INTO gift_end_feedback (telegram_id, reason) SELECT telegram_id, $2 FROM users WHERE telegram_id=$1
           ON CONFLICT (telegram_id) DO UPDATE SET reason=EXCLUDED.reason, created_at=NOW()""",
        int(telegram_id), reason)
    if reason == "payment":
        # A day's rest, then the regular payment reminders may speak again.
        await db._pool_req().execute(
            """UPDATE users SET marketing_pause_started_at=NOW(), marketing_pause_until=NOW()+INTERVAL '1 day'
               WHERE telegram_id=$1""", int(telegram_id))
    return True


async def stats(days: int = 30) -> list[dict]:
    rows = await db._pool_req().fetch(
        """SELECT reason, COUNT(*)::int AS users FROM gift_end_feedback
           WHERE created_at >= NOW() - ($1::int * INTERVAL '1 day') GROUP BY reason ORDER BY 2 DESC""", int(days))
    return [{**dict(row), "label": REASONS.get(row["reason"], row["reason"])} for row in rows]
