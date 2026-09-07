from __future__ import annotations

import logging
from html import escape
from io import BytesIO
from urllib.parse import quote

from aiohttp import web
from aiogram import Bot
from aiogram.types import FSInputFile, Message

from app import db
from app.config import get_settings
from app.ticket_files import (
    MAX_FILES,
    inspect,
    public_attachment,
    store_bytes,
    stored_path,
    unlink_stored,
)

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


def serialize_messages(messages: list[dict], *, for_admin: bool) -> list[dict]:
    out = []
    for msg in messages:
        atts = [public_attachment(a, for_admin=for_admin) for a in (msg.get("attachments") or [])]
        row = {k: v for k, v in msg.items() if k != "attachments"}
        row["attachments"] = atts
        out.append(row)
    return out


def http_file_response(row: dict) -> web.StreamResponse:
    path = stored_path(str(row.get("stored_name") or ""))
    if not path:
        raise web.HTTPNotFound()
    name = str(row.get("original_name") or path.name)
    kind = str(row.get("kind") or "file")
    mime = str(row.get("mime") or "application/octet-stream")
    inline = kind == "photo" or mime.startswith("image/")
    disp = "inline" if inline else "attachment"
    return web.FileResponse(
        path,
        headers={
            "Content-Type": mime,
            "Content-Disposition": f"{disp}; filename=\"file\"; filename*=UTF-8''{quote(name)}",
            "Cache-Control": "private, max-age=3600",
        },
    )


def _prepare_uploads(raw_files: list[dict] | None) -> list[dict]:
    files = list(raw_files or [])
    if len(files) > MAX_FILES:
        raise ValueError(f"Не больше {MAX_FILES} файлов")
    prepared: list[dict] = []
    for item in files:
        data = item.get("data") or b""
        inspect(data, str(item.get("filename") or ""), str(item.get("mime") or ""))
        prepared.append(item)
    return prepared


async def _save_message_files(message_id: int, files: list[dict]) -> list[dict]:
    saved: list[dict] = []
    stored: list[str] = []
    try:
        for item in files:
            meta = store_bytes(
                item.get("data") or b"",
                str(item.get("filename") or ""),
                str(item.get("mime") or ""),
            )
            stored.append(str(meta.get("stored_name") or ""))
            row = await db.add_ticket_attachment(message_id, meta)
            saved.append(row)
    except Exception:
        for name in stored:
            unlink_stored(name)
        raise
    return saved


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
    attachments: list[dict] | None = None,
) -> dict:
    text = normalize_body(body)
    files = _prepare_uploads(attachments)
    if not text and not files:
        raise ValueError("Пустое сообщение")
    await db.upsert_user(telegram_id, username, first_name)
    ticket, created = await db.open_or_get_ticket(telegram_id, username, first_name)
    ticket_id = int(ticket["id"])
    msg = await db.add_ticket_message(ticket_id, "user", text)
    saved = await _save_message_files(int(msg["id"]), files)
    ticket = await db.get_ticket(ticket_id)
    if ack_user and bot:
        try:
            if created:
                await bot.send_message(
                    telegram_id,
                    "Тикет открыт. Пишите сюда, если нужно уточнить. Можно прислать скриншот. Ответ придёт в этот чат и в кабинет.",
                )
            else:
                await bot.send_message(telegram_id, "Сообщение добавлено в тикет.")
        except Exception:
            logger.debug("Не удалось подтвердить тикет %s", telegram_id, exc_info=True)
    if notify_admins and bot:
        await _notify_admins(bot, ticket, text, created=created, source=source, files=saved)
    return ticket


async def receive_admin_reply(
    bot: Bot | None,
    ticket_id: int,
    body: str,
    attachments: list[dict] | None = None,
) -> dict:
    text = normalize_body(body)
    files = _prepare_uploads(attachments)
    if not text and not files:
        raise ValueError("Пустое сообщение")
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        raise KeyError("Тикет не найден")
    if ticket.get("status") == "closed":
        await db.set_ticket_status(ticket_id, "open")
    msg = await db.add_ticket_message(ticket_id, "admin", text, user_waiting=False)
    saved = await _save_message_files(int(msg["id"]), files)
    ticket = await db.get_ticket(ticket_id)
    if bot:
        try:
            await _deliver_files(
                bot,
                int(ticket["telegram_id"]),
                text,
                saved,
                prefix="Ответ поддержки",
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


def _file_caption(prefix: str, body: str) -> str:
    text = (body or "").strip()
    if prefix and text:
        return f"{prefix}:\n\n{text}"
    if prefix:
        return prefix
    return text


async def _deliver_files(
    bot: Bot,
    chat_id: int,
    body: str,
    files: list[dict],
    *,
    prefix: str = "",
) -> None:
    caption = _file_caption(prefix, body)
    if not files:
        if caption:
            await bot.send_message(chat_id, caption)
        return
    long_text = len(caption) > 1000
    first_caption = "" if long_text else caption
    for i, row in enumerate(files):
        path = stored_path(str(row.get("stored_name") or ""))
        if not path:
            continue
        name = str(row.get("original_name") or path.name)
        kind = str(row.get("kind") or "file")
        media = FSInputFile(path, filename=name)
        cap = first_caption if i == 0 else None
        try:
            if kind == "photo":
                await bot.send_photo(chat_id, media, caption=cap)
            elif kind == "video":
                await bot.send_video(chat_id, media, caption=cap)
            else:
                await bot.send_document(chat_id, media, caption=cap)
        except Exception:
            await bot.send_document(chat_id, media, caption=cap)
    if long_text and caption:
        await bot.send_message(chat_id, caption)


async def _notify_admins(
    bot: Bot,
    ticket: dict,
    body: str,
    *,
    created: bool,
    source: str,
    files: list[dict] | None = None,
) -> None:
    settings = get_settings()
    tid = int(ticket["id"])
    who = escape(str(ticket.get("first_name") or "—"))
    username = ticket.get("username")
    if username:
        who += f" (@{escape(str(username))})"
    head = "Новый тикет" if created else "Сообщение в тикет"
    src = "кабинет" if source == "app" else "бот"
    preview_text = preview(body, 280)
    if preview_text == "—" and files:
        preview_text = "Вложение"
    text = (
        f"<b>{head} #{tid}</b>\n"
        f"{who} · {int(ticket['telegram_id'])}\n"
        f"Откуда: {src}\n"
        f"{escape(preview_text)}"
    )
    for admin_id in settings.admin_id_set:
        try:
            await _deliver_files(bot, admin_id, text, files or [])
        except Exception:
            continue


async def parse_ticket_request(request: web.Request) -> tuple[str, str, list[dict]]:
    ctype = request.content_type or ""
    if ctype.startswith("multipart/"):
        fields: dict[str, str] = {}
        files: list[dict] = []
        reader = await request.multipart()
        while True:
            field = await reader.next()
            if field is None:
                break
            name = field.name or ""
            if name in {"file", "files"}:
                filename = field.filename or "file"
                data = await field.read()
                if data:
                    files.append(
                        {
                            "data": data,
                            "filename": filename,
                            "mime": (field.headers.get("Content-Type") or ""),
                        }
                    )
            else:
                fields[name] = (await field.text()).strip()
        return fields.get("text") or "", fields.get("action") or "reply", files
    try:
        body = await request.json()
    except Exception:
        body = {}
    body = body or {}
    return (
        str(body.get("text") or "").strip(),
        str(body.get("action") or "reply").strip() or "reply",
        [],
    )


async def attachments_from_message(bot: Bot, message: Message) -> list[dict]:
    file_id = ""
    filename = "file"
    mime = ""
    if message.photo:
        file_id = message.photo[-1].file_id
        filename = "photo.jpg"
        mime = "image/jpeg"
    elif message.video:
        file_id = message.video.file_id
        filename = message.video.file_name or "video.mp4"
        mime = message.video.mime_type or "video/mp4"
    elif message.animation:
        file_id = message.animation.file_id
        filename = message.animation.file_name or "animation.mp4"
        mime = message.animation.mime_type or "video/mp4"
    elif message.document:
        doc = message.document
        file_id = doc.file_id
        filename = doc.file_name or "file"
        mime = doc.mime_type or ""
    else:
        return []
    buf = BytesIO()
    await bot.download(file_id, destination=buf)
    data = buf.getvalue()
    inspect(data, filename, mime)
    return [{"data": data, "filename": filename, "mime": mime}]
