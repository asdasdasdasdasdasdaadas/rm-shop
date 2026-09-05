from __future__ import annotations

import logging
from html import escape

from aiogram import Bot

from app import db
from app.balance import sync_user_billing
from app.config import get_settings
from app.keyboards import story_mod_keyboard
from app.remnawave import RemnawaveClient
from app.texts import rub_text

logger = logging.getLogger("rm-shop.story")


def _tg_username(raw: str | None) -> str:
    handle = str(raw or "").lstrip("@").strip()
    return handle


def story_admin_text(user: dict, amount: int) -> str:
    tid = int(user.get("telegram_id") or 0)
    name = escape(str(user.get("first_name") or "без имени"))
    handle = _tg_username(user.get("username"))
    nick = f"@{escape(handle)}" if handle else "нет username"
    mention = f'<a href="tg://user?id={tid}">{name}</a>'
    return (
        "История на проверку\n"
        f"ID: <code>{tid}</code>\n"
        f"Имя: {mention}\n"
        f"Telegram: {nick}\n"
        f"Награда: {escape(rub_text(amount))}\n"
        "Нажмите имя, чтобы открыть профиль."
    )


async def _edit_story_posts(bot: Bot, items: list[dict], result: str) -> None:
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
                    "Не удалось обновить заявку истории %s/%s",
                    item.get("chat_id"),
                    item.get("message_id"),
                    exc_info=True,
                )


async def close_story_admin_messages(bot: Bot, telegram_id: int, result: str) -> None:
    items = await db.pop_story_mod_messages(telegram_id)
    await _edit_story_posts(bot, items, result)


async def notify_admins_story(bot: Bot, user: dict, amount: int) -> None:
    settings = get_settings()
    if not settings.admin_id_set:
        logger.warning("ADMIN_IDS пуст: уведомление о истории некуда отправить")
        return
    tid = int(user.get("telegram_id") or 0)
    stale = await db.pop_story_mod_messages(tid)
    if stale:
        await _edit_story_posts(bot, stale, "Заявка обновлена")
    text = story_admin_text(user, amount)
    kb = story_mod_keyboard(tid, user.get("username"))
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
            logger.debug("Не удалось написать админу %s про историю", admin_id, exc_info=True)
    await db.set_story_mod_messages(tid, posted)


async def approve_story(rw: RemnawaveClient, bot: Bot, telegram_id: int) -> str:
    settings = get_settings()
    amount = int(settings.story_reward_rub or 0)
    if amount <= 0:
        return "Награда выключена"
    total = await db.approve_story_reward(telegram_id, amount)
    if total is None:
        local = await db.get_user(telegram_id)
        if local and local.get("story_rewarded_at"):
            return "Уже начислено"
        if not local or not local.get("story_pending_at"):
            return "Заявки нет"
        return "Не удалось начислить"
    await db.log_billing_event(
        telegram_id,
        "story",
        source="admin",
        amount=amount,
        balance_after=total,
        note="Награда за историю, подтверждение админа",
    )
    try:
        await sync_user_billing(rw, telegram_id, bot)
    except Exception:
        logger.debug("Не удалось синхронизировать биллинг после истории %s", telegram_id, exc_info=True)
    try:
        await bot.send_message(
            telegram_id,
            f"Историю подтвердили. На баланс начислено {rub_text(amount)}.",
        )
    except Exception:
        logger.debug("Не удалось написать пользователю про историю %s", telegram_id, exc_info=True)
    return "Начислено"


async def reject_story(bot: Bot, telegram_id: int) -> str:
    ok = await db.reject_story_check(telegram_id)
    if not ok:
        local = await db.get_user(telegram_id)
        if local and local.get("story_rewarded_at"):
            return "Уже начислено"
        return "Заявки нет"
    try:
        await bot.send_message(
            telegram_id,
            "Историю не подтвердили. Награда не начислена.",
        )
    except Exception:
        logger.debug("Не удалось написать об отказе истории %s", telegram_id, exc_info=True)
    return "Отказано"
