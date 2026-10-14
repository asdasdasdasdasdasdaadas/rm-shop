"""Optional feedback on a real, still unpaid checkout."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app import db

REASONS = {'broken':'Не заработало', 'price':'Дорого', 'payment':'Неудобно оплатить', 'later':'Пока не нужен'}


def add_question_button(markup, token):
    rows = list(markup.inline_keyboard) if markup else []
    rows.append([InlineKeyboardButton(text='Что остановило оплату?', callback_data=f'paywhy:{token}')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def answers(token):
    buttons = [InlineKeyboardButton(text=label, callback_data=f'payreason:{key}:{token}') for key,label in REASONS.items()]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[:2],buttons[2:]])


ELIGIBLE = """u.telegram_id=$1 AND u.checkout_token=$2
    AND u.checkout_started_at > NOW()-INTERVAL '24 hours'
    AND u.checkout_nudge_at IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.telegram_id=u.telegram_id AND p.created_at>=u.checkout_started_at)
    AND NOT EXISTS (SELECT 1 FROM payment_receipts p WHERE p.telegram_id=u.telegram_id AND p.created_at>=u.checkout_started_at)
    AND NOT EXISTS (SELECT 1 FROM rollypay_orders p WHERE p.telegram_id=u.telegram_id AND p.status='granted' AND p.paid_at>=u.checkout_started_at)"""

async def current(telegram_id, token):
    return await db._pool_req().fetchrow(f'SELECT u.* FROM users u WHERE {ELIGIBLE}',telegram_id,token)


async def save(telegram_id, token, reason):
    if reason not in REASONS:
        return False
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            await conn.fetchval('SELECT telegram_id FROM users WHERE telegram_id=$1 FOR UPDATE',telegram_id)
            result = await conn.fetchval(f"""INSERT INTO checkout_feedback (telegram_id,checkout_token,reason)
                SELECT u.telegram_id,u.checkout_token,$3 FROM users u WHERE {ELIGIBLE}
                ON CONFLICT DO NOTHING RETURNING telegram_id""",telegram_id,token,reason)
            if result is None:
                return False
            if reason == 'broken':
                await db.queue_connection_complaint(conn, telegram_id)
                await conn.execute("UPDATE users SET vpn_feedback='help',vpn_feedback_at=NOW() WHERE telegram_id=$1",telegram_id)
            else:
                days = {'price':7,'payment':1,'later':7}[reason]
                await conn.execute("""UPDATE users SET marketing_pause_started_at=NOW(),
                    marketing_pause_until=NOW()+$2::int*INTERVAL '1 day' WHERE telegram_id=$1""",telegram_id,days)
    return True


async def stats():
    rows=await db._pool_req().fetch("""SELECT reason,COUNT(*)::int AS responses,COUNT(DISTINCT telegram_id)::int AS users
        FROM checkout_feedback WHERE created_at>=NOW()-INTERVAL '30 days' GROUP BY reason""")
    return [{**dict(row),'label':REASONS[row['reason']]} for row in rows]
