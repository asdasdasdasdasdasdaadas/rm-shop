from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot

from app import db, runtime
from app.config import get_settings
from app.remnawave import RemnawaveClient, RemnawaveError
from app.trust import collect_due_trusts
from app.notices import notice_text
from app.texts import rub_text

logger = logging.getLogger("rm-shop.balance")
CABINET_LINK_DAYS = 10


def _billed_today(last_billed_on) -> bool:
    if last_billed_on is None:
        return False
    today = datetime.now(timezone.utc).date()
    if isinstance(last_billed_on, datetime):
        return last_billed_on.astimezone(timezone.utc).date() >= today
    return last_billed_on >= today


async def _notify_empty(bot: Bot | None, tg_id: int, price: int, warned: set[int]) -> None:
    if not bot or tg_id in warned:
        return
    warned.add(tg_id)
    try:
        await bot.send_message(
            tg_id,
            notice_text("low_balance", price=rub_text(price)),
        )
    except Exception:
        pass


async def _bill_due_device(
    rw: RemnawaveClient,
    bot: Bot | None,
    item: dict,
    price: int,
    paused: bool,
    warned: set[int],
    source: str = "cron",
) -> str:
    tg_id = int(item["telegram_id"])
    panel_id = int(item["remnawave_id"])
    device_id = int(item["id"])
    title = str(item.get("title") or "")
    if paused:
        try:
            await rw.extend_panel_user(panel_id, 1)
            await db.mark_device_billed(device_id)
            await db.log_billing_event(
                tg_id,
                "pause",
                source=source,
                device_id=device_id,
                device_title=title,
                note="Пауза тарификации, сутки без списания",
            )
            return "extended"
        except RemnawaveError:
            logger.exception("Не удалось продлить устройство %s при паузе тарификации", item["id"])
            await db.log_billing_event(
                tg_id,
                "error",
                source=source,
                device_id=device_id,
                device_title=title,
                note="Панель не продлила устройство при паузе",
            )
            return "error"
    if await db.spend_balance_rub(tg_id, price):
        try:
            await rw.extend_panel_user(panel_id, 1)
            await db.mark_device_billed(device_id)
            await db.log_billing_event(
                tg_id,
                "charge",
                source=source,
                amount=-price,
                device_id=device_id,
                device_title=title,
                note="Списание за сутки VPN",
            )
            return "extended"
        except RemnawaveError:
            await db.add_balance_rub(tg_id, price)
            logger.exception("Не удалось продлить устройство %s", item["id"])
            await db.log_billing_event(
                tg_id,
                "error",
                source=source,
                device_id=device_id,
                device_title=title,
                note="Панель не продлила, деньги вернули",
            )
            return "error"
    try:
        await rw.disable_panel_user(panel_id)
    except RemnawaveError:
        logger.exception("Не удалось отключить устройство %s", item["id"])
        await db.log_billing_event(
            tg_id,
            "error",
            source=source,
            device_id=device_id,
            device_title=title,
            note="Панель не отключила устройство",
        )
        return "error"
    await db.mark_device_billed(device_id)
    await db.log_billing_event(
        tg_id,
        "disable",
        source=source,
        device_id=device_id,
        device_title=title,
        note="Не хватило баланса на сутки",
    )
    await _notify_empty(bot, tg_id, price, warned)
    return "disabled"


async def charge_due_devices(rw: RemnawaveClient, bot: Bot | None = None) -> None:
    settings = get_settings()
    if not settings.balance_enabled:
        return
    await collect_due_trusts(bot)
    if await db.flag_on("maintenance"):
        return
    price = max(1, settings.vpn_day_price_rub)
    paused = await db.flag_on("billing_paused")
    warned: set[int] = set()
    seen: set[int] = set()
    for item in await db.devices_due_for_billing():
        seen.add(int(item["id"]))
        await _bill_due_device(rw, bot, item, price, paused, warned)
    for item in await db.devices_to_retry_disable():
        if int(item["id"]) in seen:
            continue
        await _bill_due_device(rw, bot, item, price, paused, warned)
    await send_low_balance_cabinet_links(bot)


async def sync_user_billing(
    rw: RemnawaveClient,
    telegram_id: int,
    bot: Bot | None = None,
) -> dict:
    settings = get_settings()
    result = {"extended": 0, "disabled": 0, "revived": 0}
    if not settings.balance_enabled:
        return result
    if await db.user_is_blocked(telegram_id):
        return result
    price = max(1, settings.vpn_day_price_rub)
    paused = await db.flag_on("billing_paused")
    warned: set[int] = set()
    for item in await db.list_devices(telegram_id):
        if not item.get("remnawave_id"):
            continue
        row = {
            "id": item["id"],
            "telegram_id": telegram_id,
            "remnawave_id": item["remnawave_id"],
            "title": item.get("title") or "",
        }
        if paused or not _billed_today(item.get("last_billed_on")):
            status = await _bill_due_device(rw, bot, row, price, paused, warned, source="admin")
            if status == "extended":
                result["extended"] += 1
            elif status == "disabled":
                result["disabled"] += 1
            continue
        try:
            panel = await rw.get_user_by_id(int(item["remnawave_id"]))
        except RemnawaveError:
            logger.exception("Не удалось проверить устройство %s после смены баланса", item["id"])
            continue
        status = str((panel or {}).get("status") or "").upper()
        if status == "DISABLED":
            local = await db.get_user(telegram_id)
            if int((local or {}).get("balance_rub") or 0) >= price:
                try:
                    await rw.enable_panel_user(int(item["remnawave_id"]))
                    result["revived"] += 1
                    await db.log_billing_event(
                        telegram_id,
                        "revive",
                        source="admin",
                        device_id=int(item["id"]),
                        device_title=str(item.get("title") or ""),
                        note="Включили устройство после правки баланса",
                    )
                except RemnawaveError:
                    logger.exception("Не удалось включить устройство %s после смены баланса", item["id"])
            else:
                result["disabled"] += 1
    if bot:
        await db.purge_expired_cabinet_tokens()
        await send_cabinet_link_to(bot, telegram_id)
    return result


async def send_cabinet_link_to(bot: Bot, telegram_id: int) -> bool:
    settings = get_settings()
    if not settings.balance_enabled or not settings.webapp_enabled:
        return False
    price = max(1, settings.vpn_day_price_rub)
    if telegram_id not in await db.users_needing_cabinet_link(price):
        return False
    sent = await _issue_and_send_cabinet_link(bot, telegram_id)
    return sent > 0


async def send_low_balance_cabinet_links(bot: Bot | None) -> int:
    settings = get_settings()
    if not bot or not settings.balance_enabled or not settings.webapp_enabled:
        return 0
    await db.purge_expired_cabinet_tokens()
    price = max(1, settings.vpn_day_price_rub)
    sent = 0
    for telegram_id in await db.users_needing_cabinet_link(price):
        sent += await _issue_and_send_cabinet_link(bot, telegram_id)
    if sent:
        logger.info("Ссылки на кабинет из браузера: %s", sent)
    return sent


async def _issue_and_send_cabinet_link(bot: Bot, telegram_id: int) -> int:
    settings = get_settings()
    base = (settings.webapp_public_url or runtime.webapp_url or "").rstrip("/")
    if not base.startswith("http"):
        return 0
    token = await db.issue_cabinet_token(telegram_id, CABINET_LINK_DAYS)
    url = f"{base}/?t={token}"
    text = notice_text("cabinet_link", url=url)
    try:
        await bot.send_message(telegram_id, text)
        return 1
    except Exception:
        await db.delete_cabinet_token(token)
        logger.debug("Ссылка на кабинет не ушла %s", telegram_id, exc_info=True)
        return 0
