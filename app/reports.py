from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Bot

from app import db
from app.billing import expire_human
from app.config import get_settings
from app.remnawave import RemnawaveClient, is_subscription_active
from app.sync import fetch_panel


class ReportCooldown(Exception):
    def __init__(self, wait_sec: int) -> None:
        self.wait_sec = wait_sec
        super().__init__("cooldown")


def _dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


async def submit_vpn_report(
    bot: Bot,
    rw: RemnawaveClient,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> dict:
    settings = get_settings()
    last = await db.last_vpn_report_at(telegram_id)
    last_dt = _dt(last)
    if last_dt:
        wait = timedelta(seconds=settings.vpn_report_cooldown_sec) - (datetime.now(timezone.utc) - last_dt)
        if wait.total_seconds() > 0:
            raise ReportCooldown(int(wait.total_seconds()))

    await db.upsert_user(telegram_id, username, first_name)
    panel = await fetch_panel(rw, telegram_id, force=True)
    local = await db.get_user(telegram_id)
    expire = _dt((panel or {}).get("expireAt")) or _dt((local or {}).get("expire_at"))
    status = str((panel or {}).get("status") or (local or {}).get("panel_status") or "")
    sub_url = (panel or {}).get("subscriptionUrl") or (local or {}).get("subscription_url") or ""
    uuid = str((panel or {}).get("uuid") or (local or {}).get("remnawave_uuid") or "") or None
    active = "да" if is_subscription_active(panel) else "нет"
    expire_text = expire_human(panel) if panel else (expire.astimezone().strftime("%d.%m.%Y %H:%M") if expire else "нет")
    now = datetime.now().astimezone().strftime("%d.%m.%Y %H:%M:%S")
    uname = f"@{username}" if username else "без username"
    name = first_name or "—"

    saved = await db.save_vpn_report(
        telegram_id,
        username,
        first_name,
        expire,
        status or None,
        sub_url or None,
        uuid,
    )

    log = (
        "<b>VPN не работает</b>\n\n"
        f"Время жалобы: <code>{escape(now)}</code>\n"
        f"Пользователь: {escape(name)} ({escape(uname)})\n"
        f"Telegram ID: <code>{telegram_id}</code>\n"
        f"Подписка активна: <b>{active}</b>\n"
        f"Действует до: <b>{escape(str(expire_text))}</b>\n"
        f"Статус панели: <code>{escape(status or 'нет')}</code>\n"
        f"UUID: <code>{escape(uuid or 'нет')}</code>\n"
    )
    if sub_url:
        log += f"Ссылка: <code>{escape(sub_url)}</code>"

    for admin_id in settings.admin_id_set:
        try:
            await bot.send_message(admin_id, log)
        except Exception:
            continue
    return saved
