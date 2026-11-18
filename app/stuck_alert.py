"""«Застрял на подключении»: tell the admin, once per person, that a device was added but VPN never came online.

Two hours after a new device, if the person has never been online, the admin gets a message with who it is,
which device and app, and a link to write to them. It goes to the live channel when one is set
(Настройки → живой канал), otherwise to each admin in private. Devices older than two days are not reported,
so the first run after a deploy does not dig up old cases.

«Подключился, но трафика нет»: a device added within two days went online, yet no_traffic_alert_after_minutes
after its first online it has moved less than no_traffic_alert_min_mb — VPN switched on, but sites do not open
(a provider block, the wrong app or protocol). One message per device, admin only.

«Подключения за сутки»: once a day after 10:00 Moscow time, new devices of the last day grouped by system and app —
how many work, went online without traffic, or never switched on — so a broken app or instruction shows up.
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


NO_TRAFFIC_SQL = f"""
UPDATE devices d SET no_traffic_alert_at = NOW()
FROM users u
WHERE u.telegram_id = d.telegram_id AND d.id IN (
    SELECT x.id FROM devices x JOIN users y ON y.telegram_id = x.telegram_id
    WHERE x.no_traffic_alert_at IS NULL AND x.first_online_at IS NOT NULL
      AND x.first_online_at <= NOW() - make_interval(mins => $1::int)
      AND x.first_online_at > NOW() - INTERVAL '{WITHIN_HOURS} hours'
      AND x.created_at > NOW() - INTERVAL '{WITHIN_HOURS} hours'
      AND GREATEST(COALESCE(x.lifetime_traffic_bytes, 0), COALESCE(x.used_traffic_bytes, 0)) < $2::bigint
      AND COALESCE(x.kind, '') <> 'router' AND y.blocked_at IS NULL AND y.bot_blocked_at IS NULL
    ORDER BY x.first_online_at LIMIT {BATCH})
RETURNING d.id AS device_id, d.telegram_id, u.first_name, u.username, u.trial_used, d.title, d.platform, d.client,
          d.first_online_at, GREATEST(COALESCE(d.lifetime_traffic_bytes, 0), COALESCE(d.used_traffic_bytes, 0)) AS traffic,
          EXISTS (SELECT 1 FROM tickets t WHERE t.telegram_id = d.telegram_id AND t.status <> 'closed') AS ticket
"""


def format_no_traffic(row: dict, min_mb: int) -> tuple[str, InlineKeyboardMarkup | None]:
    from app.live import _who
    from app.remnawave import format_bytes
    lines = ["⚠️ <b>Подключился, но трафика нет</b>", "", _who(row), ""]
    app_bits = " · ".join(escape(str(x)) for x in (row.get("platform"), row.get("client")) if x)
    lines.append(f"Устройство: <b>{escape(str(row.get('title') or 'без названия'))}</b>" + (f" · {app_bits}" if app_bits else ""))
    from app.remnawave import parse_dt
    lines.append(f"Онлайн впервые: {_ago(parse_dt(row.get('first_online_at')))}")
    lines.append(f"Трафик: <b>{format_bytes(int(row.get('traffic') or 0))}</b> (нужно от {int(min_mb)} МБ)")
    lines.append("Скорее всего, блокировка у провайдера или не то приложение.")
    extra = ["Подарок забран" if row.get("trial_used") else "Подарок не забран"]
    if row.get("ticket"):
        extra.append("есть обращение в поддержку")
    lines.append(" · ".join(extra) + ".")
    handle = str(row.get("username") or "").lstrip("@").strip()
    markup = (InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Написать", url=f"https://t.me/{handle}")]])
              if handle else None)
    return "\n".join(lines), markup


async def send_no_traffic(bot) -> int:
    from app.config import get_settings
    s = get_settings()
    if not s.no_traffic_alert_enabled:
        return 0
    targets = await _targets()
    if not targets:
        return 0
    min_mb = max(1, int(s.no_traffic_alert_min_mb))
    rows = [dict(r) for r in await db._pool_req().fetch(
        NO_TRAFFIC_SQL, max(1, int(s.no_traffic_alert_after_minutes)), min_mb * 1024 * 1024)]
    for row in rows:
        text, markup = format_no_traffic(row, min_mb)
        for chat in targets:
            try:
                await bot.send_message(chat, text, parse_mode="HTML", reply_markup=markup)
            except Exception:
                logger.warning("Уведомление «нет трафика» не ушло в %s", chat, exc_info=True)
    return len(rows)


DIGEST_KEY = "connect_digest_day"
DIGEST_HOUR_MSK = 10
DIGEST_SQL = """
SELECT COALESCE(NULLIF(d.platform, ''), 'Система не указана') AS platform,
       COALESCE(NULLIF(d.client, ''), 'приложение не указано') AS client,
       COUNT(*)::int AS total,
       COUNT(*) FILTER (WHERE GREATEST(COALESCE(d.lifetime_traffic_bytes,0), COALESCE(d.used_traffic_bytes,0)) >= $1::bigint)::int AS works,
       COUNT(*) FILTER (WHERE d.first_online_at IS NOT NULL
           AND GREATEST(COALESCE(d.lifetime_traffic_bytes,0), COALESCE(d.used_traffic_bytes,0)) < $1::bigint)::int AS no_traffic,
       COUNT(*) FILTER (WHERE d.first_online_at IS NULL
           AND GREATEST(COALESCE(d.lifetime_traffic_bytes,0), COALESCE(d.used_traffic_bytes,0)) < $1::bigint)::int AS never
FROM devices d JOIN users u ON u.telegram_id = d.telegram_id
WHERE d.created_at > NOW() - INTERVAL '26 hours' AND d.created_at <= NOW() - INTERVAL '2 hours'
  AND COALESCE(d.kind, '') <> 'router' AND u.blocked_at IS NULL
GROUP BY 1, 2
"""


def _pct(part: int, total: int) -> int:
    return round(part * 100 / total) if total else 0


def format_digest(groups: list[dict]) -> str | None:
    """«Подключения за сутки»: new devices by system and app, how many work, how many went online
    without traffic and how many never switched on. None when there were no new devices."""
    total = sum(int(g["total"]) for g in groups)
    if not total:
        return None
    works = sum(int(g["works"]) for g in groups)
    lines = ["📊 <b>Подключения за сутки</b>", "",
             f"Новых устройств: <b>{total}</b> · заработало <b>{works}</b> ({_pct(works, total)}%)", ""]
    bad = lambda g: int(g["no_traffic"]) + int(g["never"])
    for g in sorted(groups, key=lambda g: (-bad(g), -int(g["total"]), str(g["platform"]))):
        name = f"{escape(str(g['platform']))} · {escape(str(g['client']))}"
        n, problems = int(g["total"]), bad(g)
        if not problems:
            lines.append(f"✅ {name} — все {n} работают")
            continue
        bits = []
        if int(g["no_traffic"]):
            bits.append(f"{int(g['no_traffic'])} без трафика")
        if int(g["never"]):
            bits.append(f"{int(g['never'])} не включались")
        mark = "🔴" if n >= 3 and problems * 2 > n else "🟡"
        lines.append(f"{mark} {name} — {', '.join(bits)} из {n}")
    worst = [g for g in groups if int(g["total"]) >= 3 and bad(g) * 2 > int(g["total"])]
    if worst:
        w = max(worst, key=lambda g: (bad(g) / int(g["total"]), int(g["total"])))
        lines += ["", f"Хуже всего: <b>{escape(str(w['platform']))} · {escape(str(w['client']))}</b> — "
                      f"не работает у {_pct(bad(w), int(w['total']))}%. Проверьте инструкцию и протокол для этого приложения."]
    lines += ["", "Без трафика — VPN включился, но меньше порога из настроек. Не включались — ни разу не были онлайн."]
    return "\n".join(lines)


async def send_digest(bot, now: datetime | None = None) -> bool:
    """Once a day after 10:00 Moscow time, to the live channel or the admins."""
    from datetime import timedelta
    from app.config import get_settings
    s = get_settings()
    if not s.connect_digest_enabled:
        return False
    msk = (now or datetime.now(timezone.utc)).astimezone(timezone(timedelta(hours=3)))
    day = msk.date().isoformat()
    if msk.hour < DIGEST_HOUR_MSK or await db.get_kv(DIGEST_KEY) == day:
        return False
    targets = await _targets()
    if not targets:
        return False
    await db.set_kv(DIGEST_KEY, day)
    min_bytes = max(1, int(s.no_traffic_alert_min_mb)) * 1024 * 1024
    text = format_digest([dict(r) for r in await db._pool_req().fetch(DIGEST_SQL, min_bytes)])
    if not text:
        return False
    for chat in targets:
        try:
            await bot.send_message(chat, text, parse_mode="HTML")
        except Exception:
            logger.warning("Сводка подключений не ушла в %s", chat, exc_info=True)
    return True


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
            await send_no_traffic(bot)
            await send_digest(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Уведомления «застрял на подключении»")
        await asyncio.sleep(300)
