from __future__ import annotations

import asyncio
import logging
from html import escape

from aiogram import Bot

from app import db, runtime
from app.config import get_settings
from app.remnawave import panel_first_connected_at, panel_online_at
from app.tg_err import telegram_fail_reason

logger = logging.getLogger("rm-shop.live")


def _chat_id():
    raw = str(getattr(get_settings(), "admin_live_chat_id", "") or "").strip()
    if not raw:
        return None
    if raw.lstrip("-").isdigit():
        return int(raw)
    return raw


def _who(user: dict | None, telegram_id: int | None = None) -> str:
    data = user or {}
    tid = int(data.get("telegram_id") or telegram_id or 0)
    name = escape(str(data.get("first_name") or "без имени"))
    handle = str(data.get("username") or "").lstrip("@").strip()
    nick = f"@{escape(handle)}" if handle else "нет username"
    if tid:
        mention = f'<a href="tg://user?id={tid}">{name}</a>'
        return f"{mention} · {nick} · <code>{tid}</code>"
    return f"{name} · {nick}"


async def _send(text: str) -> None:
    chat = _chat_id()
    bot: Bot | None = getattr(runtime, "bot", None)
    if not chat:
        return
    if bot is None:
        logger.debug("Живой канал: бот ещё не готов")
        return
    try:
        await bot.send_message(chat, text)
    except Exception as exc:
        logger.warning("Живой канал: не отправилось (%s)", telegram_fail_reason(exc))


def post(text: str) -> None:
    if not _chat_id():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_send(text))


def paid(user: dict | None, *, amount: int, title: str, repeat: bool) -> None:
    head = "Продлил" if repeat else "Оплатил"
    bits = [head, _who(user)]
    if amount:
        bits.append(f"{amount} ₽")
    elif title:
        bits.append(escape(str(title)))
    post("\n".join(bits))


def invited(referrer: dict | None, invitee: dict | None) -> None:
    post(
        "Пригласил\n"
        f"Кто: {_who(referrer)}\n"
        f"Кого: {_who(invitee)}"
    )


def story_posted(user: dict | None) -> None:
    post("Выложил историю\n" + _who(user))


def first_online(user: dict | None) -> None:
    post("Подключился первый раз\n" + _who(user))


async def note_panel_online(telegram_id: int, panel: dict | None) -> None:
    if not panel:
        return
    if not (panel_online_at(panel) or panel_first_connected_at(panel)):
        return
    user = await db.claim_first_online(telegram_id)
    if user:
        first_online(user)


async def note_first_online_from_panel_ids(panel_ids: list[int]) -> None:
    ids = [int(x) for x in panel_ids if x]
    if not ids:
        return
    for user in await db.claim_first_online_for_panel_ids(ids):
        first_online(user)


async def note_first_online_from_panels(panels: list[dict]) -> None:
    ids: list[int] = []
    for item in panels:
        if not isinstance(item, dict):
            continue
        if not (panel_online_at(item) or panel_first_connected_at(item)):
            continue
        raw = item.get("id")
        if raw is not None and str(raw).isdigit():
            ids.append(int(raw))
    await note_first_online_from_panel_ids(ids)
