"""«Спящие» and the «Что помешало?» survey.

The survey goes out as a broadcast (templates why_nodevice / why_offline in app/admin.py) to people who never
used VPN. Each answer does something at once:
  setup  — «Не разобрался, как подключить»: the connect wizard and support;
  broken — «Не заработал»: opens a support ticket with what we know about the device;
  price  — «Дорого»: what a day costs and that only added devices are charged;
  later  — «Пока не нужен»: the person becomes a sleeper, the bot stops writing for 90 days.
The last answer per person is kept in why_answers; the dashboard «Спящие» widget counts them.

The panel cleanup: once a day, devices that never carried traffic panel_cleanup_days after being added are
removed from Remnawave and from the cabinet (each is its own panel user). Adding a device again takes a minute.
The very first cleanup waits FIRST_DELAY_DAYS, so the survey can reach those people first.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.sleepers")
router = Router()

CLEANUP_FROM_KEY = "panel_cleanup_from"
FIRST_DELAY_DAYS = 3

ANSWERS = {
    "setup": "Не разобрался, как подключить",
    "broken": "Не заработал",
    "price": "Дорого",
    "later": "Пока не нужен",
}


def why_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ANSWERS["setup"], callback_data="why:setup")],
        [InlineKeyboardButton(text=ANSWERS["broken"], callback_data="why:broken")],
        [InlineKeyboardButton(text=ANSWERS["price"], callback_data="why:price"),
         InlineKeyboardButton(text=ANSWERS["later"], callback_data="why:later")],
    ])


def _support_button() -> InlineKeyboardButton:
    from app.keyboards import support_url, support_webapp_button
    return support_webapp_button() or InlineKeyboardButton(text="Поддержка", url=support_url())


def _connect_button() -> InlineKeyboardButton | None:
    from app.keyboards import mini_app_screen
    app = mini_app_screen("connect")
    return InlineKeyboardButton(text="Подключить VPN", web_app=app, style="success") if app else None


def reply_for(answer: str) -> tuple[str, InlineKeyboardMarkup | None]:
    connect = _connect_button()
    if answer == "setup":
        rows = [[connect]] if connect else []
        rows.append([_support_button()])
        return ("Давайте по шагам 👇\n\nНажмите «Подключить VPN», выберите своё устройство — бот покажет, какое "
                "приложение поставить и куда нажать. Займёт пару минут. Застрянете — напишите в поддержку, "
                "поможем прямо в чате."), InlineKeyboardMarkup(inline_keyboard=rows)
    if answer == "price":
        price = max(1, int(get_settings().vpn_day_price_rub))
        min_topup = max(1, int(get_settings().balance_topup_min))
        rows = [[connect]] if connect else []
        return (f"Сутки VPN — {price} ₽ за одно устройство. Деньги списываются только за добавленные устройства "
                f"и только за дни, когда они есть: удалили устройство — списания прекратились.\n\n"
                f"Пополнить можно от {min_topup} ₽, без подписок и автоплатежей."), (
                    InlineKeyboardMarkup(inline_keyboard=rows) if rows else None)
    if answer == "later":
        return ("Понятно, не будем беспокоить 👌\n\nКогда VPN понадобится — бот здесь, "
                "подключение займёт пару минут."), None
    return "", None


async def _device_line(telegram_id: int) -> str:
    row = await db._pool_req().fetchrow(
        """SELECT title, platform, client FROM devices WHERE telegram_id=$1 AND COALESCE(kind,'') <> 'router'
           ORDER BY created_at DESC LIMIT 1""", int(telegram_id))
    if not row:
        return "Устройства нет."
    bits = " · ".join(str(x) for x in (row["platform"], row["client"]) if x)
    return f"Устройство: {row['title'] or 'без названия'}" + (f" ({bits})" if bits else "") + ", VPN ни разу не подключался."


@router.callback_query(F.data.startswith("why:"))
async def on_answer(callback: CallbackQuery) -> None:
    answer = (callback.data or "").split(":", 1)[1]
    if answer not in ANSWERS:
        await callback.answer()
        return
    user = callback.from_user
    await db.save_why_answer(user.id, answer)
    if answer == "broken":
        from app import tickets
        body = f"Опрос «Что помешало?»: VPN не заработал.\n{await _device_line(user.id)}"
        try:
            await tickets.receive_user_message(callback.bot, telegram_id=user.id, username=user.username,
                                               first_name=user.first_name, body=body, source="survey")
        except Exception:
            logger.exception("Обращение из опроса не создалось для %s", user.id)
            await callback.message.answer("Напишите, что происходит, — ответим здесь.",
                                          reply_markup=InlineKeyboardMarkup(inline_keyboard=[[_support_button()]]))
        await callback.answer("Открыли обращение в поддержку")
        return
    text, markup = reply_for(answer)
    await callback.answer("Спасибо за ответ")
    if callback.message:
        await callback.message.answer(text, reply_markup=markup)


async def cleanup_panel(rw) -> int:
    """Remove never-online devices older than panel_cleanup_days from the panel and the cabinet."""
    s = get_settings()
    if not s.panel_cleanup_enabled:
        return 0
    # The first cleanup waits 3 days after this feature arrived, so «Что помешало?» can still reach
    # people whose device never connected.
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start = await db.get_kv(CLEANUP_FROM_KEY)
    if not start:
        await db.set_kv(CLEANUP_FROM_KEY, (now + timedelta(days=FIRST_DELAY_DAYS)).isoformat())
        return 0
    try:
        if now < datetime.fromisoformat(start):
            return 0
    except ValueError:
        pass
    from app.remnawave import RemnawaveError
    removed = 0
    for item in await db.never_online_devices(max(7, int(s.panel_cleanup_days))):
        if item.get("remnawave_id"):
            try:
                await rw.delete_panel_user(int(item["remnawave_id"]))
            except RemnawaveError:
                logger.warning("Чистка панели: устройство %s не удалилось", item["id"], exc_info=True)
                continue
        gone = await db.drop_never_online_device(int(item["id"]))
        if not gone:
            continue
        removed += 1
        await db.log_billing_event(int(gone["telegram_id"]), "device_delete", source="cleanup",
                                   device_id=int(gone["id"]), device_title=str(gone.get("title") or ""),
                                   note=f"Удалено: не подключалось {int(s.panel_cleanup_days)} дней")
    if removed:
        logger.info("Чистка панели: удалено устройств без подключения: %s", removed)
    return removed


async def cleanup_loop(rw) -> None:
    await asyncio.sleep(15 * 60)
    while True:
        try:
            while await cleanup_panel(rw) >= 50:  # a big first run goes in batches
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Чистка панели")
        await asyncio.sleep(24 * 60 * 60)
