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
    mention = f'<a href="tg://user?id={tid}">{name}</a>'
    details = escape(str(payout.get("details") or "").strip() or "не указаны")
    return (
        "Заявка на вывод реферальных\n"
        f"ID: <code>{tid}</code>\n"
        f"Имя: {mention}\n"
        f"Telegram: {nick}\n"
        f"Сумма: {escape(rub_text(int(payout.get('amount') or 0)))}\n"
        f"Реквизиты: {details}\n"
        "Нажмите имя, чтобы открыть профиль."
    )


async def _edit_payout_posts(bot: Bot, items: list[dict], result: str) -> None:
    line = escape((result or "").rstrip(".")) + "."
    for item in items:
        html = str(item.get("html") or "").strip()
        text = f"{html}\n\n{line}" if html else line
        try:
            await bot.edit_message_text(
                text,
                chat_id=int(item["chat_id"]),
                message_id=int(item["message_id"]),
                reply_markup=None,
            )
        except Exception:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=int(item["chat_id"]),
                    message_id=int(item["message_id"]),
                    reply_markup=None,
                )
            except Exception:
                logger.debug(
                    "Не удалось обновить заявку вывода %s/%s",
                    item.get("chat_id"),
                    item.get("message_id"),
                    exc_info=True,
                )


async def close_payout_admin_messages(bot: Bot, payout_id: int, result: str) -> None:
    items = await db.pop_mod_messages("payout", payout_id)
    await _edit_payout_posts(bot, items, result)


async def notify_admins_payout(bot: Bot, user: dict, payout: dict) -> None:
    settings = get_settings()
    if not settings.admin_id_set:
        logger.warning("ADMIN_IDS пуст: уведомление о выводе некуда отправить")
        return
    payout_id = int(payout["id"])
    stale = await db.pop_mod_messages("payout", payout_id)
    if stale:
        await _edit_payout_posts(bot, stale, "Заявка обновлена")
    tid = int(user.get("telegram_id") or payout.get("telegram_id") or 0)
    text = payout_admin_text(user, payout)
    kb = payout_mod_keyboard(payout_id, user.get("username"), tid)
    posted: list[dict] = []
    for admin_id in settings.admin_id_set:
        try:
            msg = await bot.send_message(admin_id, text, reply_markup=kb)
            posted.append(
                {
                    "chat_id": msg.chat.id,
                    "message_id": msg.message_id,
                    "html": text,
                }
            )
        except Exception:
            logger.debug("Не удалось написать админу %s про вывод", admin_id, exc_info=True)
    await db.set_mod_messages("payout", payout_id, posted)


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
        await close_payout_admin_messages(bot, payout_id, "Заявка не найдена")
        return "Заявка не найдена"
    result = await db.resolve_referral_payout(payout_id, action, admin_id)
    if result != "ok":
        await close_payout_admin_messages(bot, payout_id, result)
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
    await close_payout_admin_messages(bot, payout_id, label)
    return label
