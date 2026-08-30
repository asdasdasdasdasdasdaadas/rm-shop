from __future__ import annotations

import logging

from aiogram import Bot

from app import db
from app.config import get_settings
from app.remnawave import RemnawaveClient, RemnawaveError

logger = logging.getLogger("rm-shop.balance")


async def charge_due_devices(rw: RemnawaveClient, bot: Bot | None = None) -> None:
    settings = get_settings()
    if not settings.balance_enabled:
        return
    price = max(1, settings.vpn_day_price_rub)
    due = await db.devices_due_for_billing()
    warned: set[int] = set()
    for item in due:
        tg_id = int(item["telegram_id"])
        panel_id = int(item["remnawave_id"])
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
                    f"Стоимость: {price} руб. за устройство в день. "
                    "Пополните баланс. Вывод средств недоступен.",
                )
            except Exception:
                pass
