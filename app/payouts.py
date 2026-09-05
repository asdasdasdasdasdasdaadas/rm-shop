from __future__ import annotations

import logging
from html import escape

from aiogram import Bot

from app import db
from app.config import get_settings, referral_is_payout
from app.keyboards import payout_mod_keyboard
from app.notices import notice_text
from app.referrals import referral_payout_public
from app.texts import rub_text

logger = logging.getLogger("rm-shop.payouts")


def _tg_username(raw: str | None) -> str:
    return str(raw or "").lstrip("@").strip()


def payout_admin_text(user: dict, payout: dict) -> str:
    tid = int(user.get("telegram_id") or payout.get("telegram_id") or 0)
    name = escape(str(user.get("first_name") or "без имени"))
    handle = _tg_username(user.get("username"))
    nick = f"@{escape(handle)}" if handle else "нет username"
    details = escape(str(payout.get("details") or "").strip() or "не указаны")
    return (
        "Заявка на вывод реферальных\n"
        f"ID: <code>{tid}</code>\n"
        f"Имя: {name}\n"
        f"Telegram: {nick}\n"
        f"Сумма: {escape(rub_text(int(payout.get('amount') or 0)))}\n"
        f"Реквизиты: {details}"
    )


async def notify_admins_payout(bot: Bot, user: dict, payout: dict) -> None:
    settings = get_settings()
    if not settings.admin_id_set:
        logger.warning("ADMIN_IDS пуст: уведомление о выводе некуда отправить")
        return
    text = payout_admin_text(user, payout)
    kb = payout_mod_keyboard(int(payout["id"]), user.get("username"), int(user.get("telegram_id") or 0))
    for admin_id in settings.admin_id_set:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb)
        except Exception:
            logger.debug("Не удалось написать админу %s про вывод", admin_id, exc_info=True)


async def request_referral_payout(bot: Bot, telegram_id: int, details: str) -> tuple[bool, str]:
    settings = get_settings()
    if not (settings.balance_enabled and referral_is_payout()):
        return False, "Вывод реферальных сейчас выключен"
    note = (details or "").strip()
    if len(note) < 6:
        return False, "Укажите телефон СБП или другие реквизиты"
    if len(note) > 200:
        return False, "Реквизиты слишком длинные"
    wallet = await db.referral_wallet(telegram_id)
    view = referral_payout_public(wallet)
    if int(wallet.get("pending") or 0) > 0:
        return False, "Предыдущая заявка ещё на проверке"
    amount = int(wallet.get("available") or 0)
    if amount < int(view["referral_payout_min"]):
        return False, f"Нужно накопить {rub_text(int(view['referral_payout_min']))} реферальных"
    payout = await db.create_referral_payout(telegram_id, amount, note)
    if not payout:
        return False, "Не удалось создать заявку. Проверьте баланс"
    await db.log_billing_event(
        telegram_id,
        "referral_payout",
        source="user",
        amount=-amount,
        note=f"Заявка на вывод #{payout['id']}",
    )
    user = await db.get_user(telegram_id) or {"telegram_id": telegram_id}
    await notify_admins_payout(bot, user, payout)
    return True, notice_text("referral_payout_submitted", amount=rub_text(amount))


async def finish_referral_payout(bot: Bot, payout_id: int, action: str, admin_id: int | None) -> str:
    payout = await db.get_referral_payout(payout_id)
    if not payout:
        return "Заявка не найдена"
    result = await db.resolve_referral_payout(payout_id, action, admin_id)
    if result != "ok":
        return result
    telegram_id = int(payout["telegram_id"])
    amount = rub_text(int(payout["amount"] or 0))
    after = await db.get_user(telegram_id)
    balance_after = int((after or {}).get("balance_rub") or 0)
    if action == "paid":
        await db.log_billing_event(
            telegram_id,
            "referral_payout",
            source="admin",
            amount=0,
            balance_after=balance_after,
            note=f"Выплата #{payout_id}",
        )
        text = notice_text("referral_payout_paid", amount=amount)
        label = "Выплачено"
    else:
        await db.log_billing_event(
            telegram_id,
            "referral_payout",
            source="admin",
            amount=int(payout["amount"] or 0),
            balance_after=balance_after,
            note=f"Отказ по заявке #{payout_id}",
        )
        text = notice_text("referral_payout_rejected", amount=amount)
        label = "Отказано"
    try:
        await bot.send_message(telegram_id, text)
    except Exception:
        logger.debug("Не удалось написать %s про вывод", telegram_id, exc_info=True)
    return label
