from __future__ import annotations

import logging

from aiogram import Bot

from app import db, runtime
from app.config import get_settings
from app.remnawave import RemnawaveClient, RemnawaveError
from app.trust import collect_due_trusts
from app.texts import rub_text

logger = logging.getLogger("rm-shop.balance")
CABINET_LINK_DAYS = 10


async def charge_due_devices(rw: RemnawaveClient, bot: Bot | None = None) -> None:
    settings = get_settings()
    if not settings.balance_enabled:
        return
    await collect_due_trusts(bot)
    if await db.flag_on("maintenance"):
        return
    price = max(1, settings.vpn_day_price_rub)
    paused = await db.flag_on("billing_paused")
    due = await db.devices_due_for_billing()
    warned: set[int] = set()
    for item in due:
        tg_id = int(item["telegram_id"])
        panel_id = int(item["remnawave_id"])
        if paused:
            try:
                await rw.extend_panel_user(panel_id, 1)
                await db.mark_device_billed(int(item["id"]))
            except RemnawaveError:
                logger.exception("Не удалось продлить устройство %s при паузе тарификации", item["id"])
            continue
        if await db.spend_balance_rub(tg_id, price):
            try:
                await rw.extend_panel_user(panel_id, 1)
                await db.mark_device_billed(int(item["id"]))
            except RemnawaveError:
                await db.add_balance_rub(tg_id, price)
                logger.exception("Не удалось продлить устройство %s", item["id"])
            continue
        try:
            await rw.disable_panel_user(panel_id)
        except RemnawaveError:
            logger.exception("Не удалось отключить устройство %s", item["id"])
        if bot and tg_id not in warned:
            warned.add(tg_id)
            try:
                await bot.send_message(
                    tg_id,
                    "На балансе не хватает средств на сутки VPN. "
                    f"Стоимость: {rub_text(price)} за устройство в день. "
                    "Пополните баланс.",
                )
            except Exception:
                pass

    await send_low_balance_cabinet_links(bot)


async def send_low_balance_cabinet_links(bot: Bot | None) -> int:
    settings = get_settings()
    if not bot or not settings.balance_enabled or not settings.webapp_enabled:
        return 0
    base = (settings.webapp_public_url or runtime.webapp_url or "").rstrip("/")
    if not base.startswith("http"):
        return 0
    await db.purge_expired_cabinet_tokens()
    price = max(1, settings.vpn_day_price_rub)
    sent = 0
    for telegram_id in await db.users_needing_cabinet_link(price):
        token = await db.issue_cabinet_token(telegram_id, CABINET_LINK_DAYS)
        url = f"{base}/?t={token}"
        text = (
            "Баланса хватит меньше чем на двое суток. "
            "Если VPN отключится, Telegram может быть недоступен.\n\n"
            "Кабинет из браузера, без VPN. Ссылка действует 10 дней:\n"
            f"{url}"
        )
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except Exception:
            await db.delete_cabinet_token(token)
            logger.debug("Ссылка на кабинет не ушла %s", telegram_id, exc_info=True)
    if sent:
        logger.info("Ссылки на кабинет из браузера: %s", sent)
    return sent
