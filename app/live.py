from __future__ import annotations

import asyncio
import json
import logging
import re
from html import escape
from typing import Any

from aiogram import Bot, Router
from aiogram.types import ChatMemberUpdated

from app import db, runtime
from app.config import get_settings
from app.remnawave import panel_first_connected_at, panel_online_at
from app.tg_err import telegram_fail_reason

logger = logging.getLogger("rm-shop.live")
router = Router()
HINT_KEY = "live_chat_hint"
_C_LINK = re.compile(r"(?:t\.me|telegram\.me)/c/(\d+)", re.I)


def parse_live_chat_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 200:
        raise ValueError("Живой канал: слишком длинная строка")
    low = text.lower()
    if "joinchat" in low or "t.me/+" in low or "telegram.me/+" in low or text.startswith("+"):
        raise ValueError(
            "Приватный канал: ссылка-приглашение не подходит. "
            "Добавьте бота администратором канала — id появится в форме. "
            "Либо вставьте id вида -100... или ссылку t.me/c/..."
        )
    found = _C_LINK.search(text.replace("https://", "").replace("http://", ""))
    if found:
        return "-100" + found.group(1)
    if re.match(r"https?://", text, re.I) or low.startswith("t.me/"):
        path = text.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        text = path
    if text.lstrip("-").isdigit():
        if text.startswith("-"):
            return text
        if text.startswith("100") and len(text) >= 12:
            return "-" + text
        return text
    handle = text[1:] if text.startswith("@") else text
    handle = handle.strip()
    if handle and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,}", handle):
        return "@" + handle
    raise ValueError(
        "Публичный канал: @username. Приватный: id -100... или ссылка t.me/c/.... "
        "Не пригласительная ссылка."
    )


def _chat_id():
    try:
        raw = parse_live_chat_id(getattr(get_settings(), "admin_live_chat_id", "") or "")
    except ValueError:
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


async def get_live_chat_hint() -> dict | None:
    raw = (await db.get_kv(HINT_KEY)).strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or not data.get("id"):
        return None
    return data


async def remember_live_chat(chat) -> None:
    if not chat or getattr(chat, "type", "") not in {"channel", "supergroup"}:
        return
    settings = get_settings()
    req = str(settings.required_channel_id or "").strip()
    cid = str(chat.id)
    uname = str(getattr(chat, "username", None) or "").lstrip("@").lower()
    req_name = req.lstrip("@").lower()
    if req and (cid == req or (uname and uname == req_name)):
        return
    try:
        if parse_live_chat_id(req) == cid:
            return
    except ValueError:
        pass
    await db.set_kv(
        HINT_KEY,
        json.dumps(
            {
                "id": cid,
                "title": str(getattr(chat, "title", None) or ""),
                "username": str(getattr(chat, "username", None) or ""),
                "type": str(chat.type),
            },
            ensure_ascii=False,
        ),
    )


async def verify_live_chat(value: str) -> None:
    raw = parse_live_chat_id(value)
    if not raw:
        return
    bot: Bot | None = getattr(runtime, "bot", None)
    if bot is None:
        return
    chat = int(raw) if raw.lstrip("-").isdigit() else raw
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat, me.id)
    except Exception as exc:
        raise ValueError(
            "Бот не видит этот чат. Для приватного канала добавьте бота администратором "
            "(право публиковать сообщения), затем укажите id -100... или ссылку t.me/c/.... "
            f"Telegram: {telegram_fail_reason(exc)}"
        ) from exc
    status = str(getattr(member, "status", "") or "")
    if status not in {"administrator", "creator"}:
        raise ValueError("Бот должен быть администратором канала")
    can_post = getattr(member, "can_post_messages", None)
    if status == "administrator" and can_post is False:
        raise ValueError("Дайте боту в канале право публиковать сообщения")


@router.my_chat_member()
async def on_bot_chat_member(event: ChatMemberUpdated) -> None:
    new = event.new_chat_member
    if str(getattr(new, "status", "") or "") not in {"administrator", "creator"}:
        return
    try:
        await remember_live_chat(event.chat)
    except Exception:
        logger.debug("Не удалось запомнить канал для живых событий", exc_info=True)
