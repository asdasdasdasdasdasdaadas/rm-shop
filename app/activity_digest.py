"""Daily Moscow-time digest; failed delivery remains eligible for retry."""
import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app import db

logger = logging.getLogger(__name__)
MSK = ZoneInfo('Europe/Moscow')
LABELS = {'invite': 'Нажали «Пригласить друзей»', 'share': 'Нажали «Поделиться»',
          'copy': 'Копировали приглашение', 'about': 'Открыли «О сервисе»',
          'cabinet': 'Открыли кабинет', 'gift_view': 'Посмотрели подарок'}


async def record(telegram_id, action, source):
    if action not in LABELS or source not in {'bot', 'web'}:
        return
    await db._pool_req().execute('''INSERT INTO admin_activity_daily(day,telegram_id,action,source)
        VALUES ((NOW() AT TIME ZONE 'Europe/Moscow')::date,$1,$2,$3)
        ON CONFLICT (day,telegram_id,action,source)
        DO UPDATE SET events=admin_activity_daily.events+1''', int(telegram_id), action, source)


def format_digest(day, rows, users):
    from app.live import _heading
    lines = [_heading('history', '🕔', 'Активность за ' + day.strftime('%d.%m.%Y')),
             '', f'Пользователей: <b>{users}</b>', '']
    for row in rows:
        lines.append(f'{LABELS[row["action"]]}: <b>{row["events"]}</b> · людей: <b>{row["users"]}</b>')
    lines.extend(['', '<i>Действия в боте и веб-кабинете. Период: 00:00–24:00 МСК.</i>'])
    return '\n'.join(lines)


async def send_due(bot, now=None):
    from app.live import _chat_id
    chat = _chat_id()
    now = (now or datetime.now(timezone.utc)).astimezone(MSK)
    if not chat or now.hour < 9:
        return False
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            # Serialize workers through delivery and durable acknowledgement.
            if not await conn.fetchval('SELECT pg_try_advisory_xact_lock(73619430)'):
                return False
            day = await conn.fetchval('''SELECT MIN(a.day) FROM admin_activity_daily a
                WHERE a.day < $1 AND NOT EXISTS
                (SELECT 1 FROM admin_activity_digests d WHERE d.day=a.day)''', now.date())
            if day is None:
                return False
            rows = await conn.fetch('''SELECT action,SUM(events)::bigint AS events,
                COUNT(DISTINCT telegram_id)::int AS users FROM admin_activity_daily
                WHERE day=$1 GROUP BY action ORDER BY action''', day)
            users = await conn.fetchval('SELECT COUNT(DISTINCT telegram_id) FROM admin_activity_daily WHERE day=$1', day)
            await bot.send_message(chat, format_digest(day, rows, users), parse_mode='HTML', request_timeout=30)
            await conn.execute('INSERT INTO admin_activity_digests(day) VALUES ($1)', day)
    return True


async def digest_loop(bot):
    while True:
        try:
            await send_due(bot)
        except Exception:
            logger.exception('Daily activity digest will retry')
        await asyncio.sleep(60)
