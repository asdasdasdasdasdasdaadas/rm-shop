"""«Застрял на подключении»: tell the admin, once per person, that a device was added but VPN never came online.

Two hours after a new device, if the person has never been online, the admin gets a message with who it is,
which device and app, and a link to write to them. It goes to the live channel when one is set
(Настройки → живой канал), otherwise to each admin in private. Devices older than two days are not reported,
so the first run after a deploy does not dig up old cases.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app import db

logger = logging.getLogger("rm-shop.stuck")

AFTER_HOURS = 2
WITHIN_HOURS = 48
BATCH = 20

CLAIM_SQL = f"""
UPDATE users u SET stuck_alert_at = NOW()
WHERE u.stuck_alert_at IS NULL
  AND u.telegram_id IN (
      SELECT DISTINCT x.telegram_id FROM users x JOIN devices d ON d.telegram_id = x.telegram_id
      WHERE x.stuck_alert_at IS NULL AND x.first_online_at IS NULL
        AND x.blocked_at IS NULL AND x.bot_blocked_at IS NULL
        AND d.last_online_at IS NULL AND COALESCE(d.kind, '') <> 'router'
        AND d.created_at <= NOW() - INTERVAL '{AFTER_HOURS} hours'
        AND d.created_at > NOW() - INTERVAL '{WITHIN_HOURS} hours'
      LIMIT {BATCH})
RETURNING u.telegram_id, u.first_name, u.username, u.trial_used, u.balance_rub
"""

DETAILS_SQL = """
SELECT d.title, d.platform, d.client, d.created_at,
       (SELECT COUNT(*) FROM devices x WHERE x.telegram_id = d.telegram_id) AS devices,
       EXISTS (SELECT 1 FROM tickets t WHERE t.telegram_id = d.telegram_id AND t.status <> 'closed') AS ticket
FROM devices d WHERE d.telegram_id = $1 AND COALESCE(d.kind, '') <> 'router'
ORDER BY d.created_at DESC LIMIT 1
"""


def _ago(when: datetime | None) -> str:
    if not when:
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    minutes = max(0, int((datetime.now(timezone.utc) - when).total_seconds() // 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч {minutes} мин назад" if hours else f"{minutes} мин назад"


def format_alert(user: dict, device: dict | None) -> tuple[str, InlineKeyboardMarkup | None]:
    from app.live import _heading, _who
    lines = [_heading("connect", "⏳", "Застрял на подключении"), "", _who(user), ""]
    if device:
        app_bits = " · ".join(escape(str(x)) for x in (device.get("platform"), device.get("client")) if x)
        lines.append(f"Устройство: <b>{escape(str(device.get('title') or 'без названия'))}</b>"
                     + (f" ({app_bits})" if app_bits else "") + f", добавлено {_ago(device.get('created_at'))}")
        if int(device.get("devices") or 0) > 1:
            lines.append(f"Всего устройств: {int(device['devices'])}")
    lines.append("VPN ещё ни разу не подключался.")
    lines.append("Подарок забран." if user.get("trial_used") else "Подарок не забран.")
    if device and device.get("ticket"):
        lines.append("Есть открытое обращение в поддержку.")
    handle = str(user.get("username") or "").lstrip("@").strip()
    markup = (InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Написать", url=f"https://t.me/{handle}")]])
              if handle else None)
    return "\n".join(lines), markup


async def _targets() -> list:
    from app.config import get_settings
    from app.live import _chat_id
    chat = _chat_id()
    return [chat] if chat else sorted(get_settings().admin_id_set)


async def send_due(bot) -> int:
    targets = await _targets()
    if not targets:
        return 0
    users = [dict(r) for r in await db._pool_req().fetch(CLAIM_SQL)]
    for user in users:
        row = await db._pool_req().fetchrow(DETAILS_SQL, int(user["telegram_id"]))
        text, markup = format_alert(user, dict(row) if row else None)
        for chat in targets:
            try:
                await bot.send_message(chat, text, parse_mode="HTML", reply_markup=markup)
            except Exception:
                logger.warning("Уведомление «застрял на подключении» не ушло в %s", chat, exc_info=True)
    return len(users)


async def stuck_alert_loop(bot) -> None:
    while True:
        try:
            await send_due(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Уведомления «застрял на подключении»")
        await asyncio.sleep(300)
