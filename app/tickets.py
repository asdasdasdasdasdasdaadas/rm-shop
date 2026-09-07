from __future__ import annotations

import logging
from html import escape

from aiogram import Bot

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.tickets")

MAX_BODY = 2000
STATUS_LABEL = {
    "open": "ждёт ответа",
    "pending": "есть ответ",
    "closed": "закрыт",
}


def preview(text: str, limit: int = 80) -> str:
    s = " ".join(str(text or "").split())
    if not s:
        return "—"
    return s if len(s) <= limit else s[: limit - 1] + "…"


def normalize_body(raw: str) -> str:
    return str(raw or "").strip()[:MAX_BODY]


async def receive_user_message(
    bot: Bot | None,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    body: str,
    source: str = "bot",
    notify_admins: bool = True,
    ack_user: bool = True,
) -> dict:
    text = normalize_body(body)
    if not text:
        raise ValueError("Пустое сообщение")
    await db.upsert_user(telegram_id, username, first_name)
    ticket, created = await db.open_or_get_ticket(telegram_id, username, first_name)
    ticket_id = int(ticket["id"])
    await db.add_ticket_message(ticket_id, "user", text)
    ticket = await db.get_ticket(ticket_id)
    if ack_user and bot:
        try:
            if created:
                await bot.send_message(
                    telegram_id,
                    "Тикет открыт. Пишите сюда, если нужно уточнить. Ответ придёт в этот чат и в кабинет.",
                )
            else:
                await bot.send_message(telegram_id, "Сообщение добавлено в тикет.")
        except Exception:
            logger.debug("Не удалось подтвердить тикет %s", telegram_id, exc_info=True)
    if notify_admins and bot:
        await _notify_admins(bot, ticket, text, created=created, source=source)
    return ticket


async def receive_admin_reply(bot: Bot | None, ticket_id: int, body: str) -> dict:
    text = normalize_body(body)
    if not text:
        raise ValueError("Пустое сообщение")
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        raise KeyError("Тикет не найден")
    if ticket.get("status") == "closed":
        await db.set_ticket_status(ticket_id, "open")
    await db.add_ticket_message(ticket_id, "admin", text, user_waiting=False)
    ticket = await db.get_ticket(ticket_id)
    if bot:
        try:
            await bot.send_message(
                int(ticket["telegram_id"]),
                f"Ответ поддержки:\n\n{text}",
            )
        except Exception:
            logger.debug("Не удалось отправить ответ тикета %s", ticket_id, exc_info=True)
    return ticket


async def close_ticket(bot: Bot | None, ticket_id: int, *, notify_user: bool = True) -> dict:
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        raise KeyError("Тикет не найден")
    if ticket.get("status") == "closed":
        return ticket
    await db.set_ticket_status(ticket_id, "closed")
    ticket = await db.get_ticket(ticket_id)
    if notify_user and bot and ticket:
        try:
            await bot.send_message(int(ticket["telegram_id"]), "Тикет закрыт. Если проблема вернётся — напишите снова.")
        except Exception:
            logger.debug("Не удалось закрыть тикет у пользователя %s", ticket_id, exc_info=True)
    return ticket


async def _notify_admins(bot: Bot, ticket: dict, body: str, *, created: bool, source: str) -> None:
    settings = get_settings()
    tid = int(ticket["id"])
    who = escape(str(ticket.get("first_name") or "—"))
    username = ticket.get("username")
    if username:
        who += f" (@{escape(str(username))})"
    head = "Новый тикет" if created else "Сообщение в тикет"
    src = "кабинет" if source == "app" else "бот"
    text = (
        f"<b>{head} #{tid}</b>\n"
        f"{who} · {int(ticket['telegram_id'])}\n"
        f"Откуда: {src}\n"
        f"{escape(preview(body, 280))}"
    )
    for admin_id in settings.admin_id_set:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            continue
