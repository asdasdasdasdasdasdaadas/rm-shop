from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
    MessageReactionUpdated,
    TelegramObject,
)

from app import db
from app.config import ROOT, get_settings
from app.trust import MAINTENANCE_TEXT

PHOTO_DIR = ROOT / "data"
PHOTO_STEM = "maintenance_photo"
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PHOTO_MAX = 10 * 1024 * 1024
FILE_ID_KEY = "maintenance_photo_file_id"


def photo_path() -> Path | None:
    if not PHOTO_DIR.is_dir():
        return None
    for path in PHOTO_DIR.glob(PHOTO_STEM + ".*"):
        if path.suffix.lower() in PHOTO_EXTS and path.is_file():
            return path
    return None


def has_photo() -> bool:
    path = photo_path()
    return bool(path and path.stat().st_size > 0)


def _ext_from_name(filename: str) -> str:
    name = (filename or "").lower()
    for ext in PHOTO_EXTS:
        if name.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def _ext_from_bytes(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:6] in {b"GIF87a", b"GIF89a"}:
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


async def save_photo(data: bytes, filename: str) -> None:
    if len(data) > PHOTO_MAX:
        raise ValueError("Картинка больше 10 МБ")
    ext = _ext_from_bytes(data) or _ext_from_name(filename)
    if ext not in PHOTO_EXTS:
        raise ValueError("Нужен файл JPG, PNG, WEBP или GIF")
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    for old in PHOTO_DIR.glob(PHOTO_STEM + ".*"):
        try:
            old.unlink()
        except OSError:
            pass
    (PHOTO_DIR / f"{PHOTO_STEM}{ext}").write_bytes(data)
    await db.set_kv(FILE_ID_KEY, "")


async def clear_photo() -> None:
    for old in PHOTO_DIR.glob(PHOTO_STEM + ".*"):
        try:
            old.unlink()
        except OSError:
            pass
    await db.set_kv(FILE_ID_KEY, "")


async def current_text() -> str:
    stored = (await db.get_kv("maintenance_notice")).strip()
    return stored or MAINTENANCE_TEXT


async def notify_user(bot: Bot, chat_id: int) -> None:
    notice = await current_text()
    path = photo_path()
    caption = notice[:1024]
    rest = notice[1024:].strip()
    if path:
        file_id = (await db.get_kv(FILE_ID_KEY)).strip()
        try:
            sent = await bot.send_photo(
                chat_id,
                file_id or FSInputFile(path),
                caption=caption,
                parse_mode=None,
            )
        except Exception:
            await db.set_kv(FILE_ID_KEY, "")
            sent = await bot.send_photo(chat_id, FSInputFile(path), caption=caption, parse_mode=None)
        if sent.photo:
            await db.set_kv(FILE_ID_KEY, sent.photo[-1].file_id)
    else:
        await bot.send_message(chat_id, notice, parse_mode=None)
    if rest:
        await bot.send_message(chat_id, rest[:4096], parse_mode=None)


def _chat_id(event: TelegramObject) -> int | None:
    if isinstance(event, Message):
        return event.chat.id
    if isinstance(event, CallbackQuery):
        msg = event.message
        chat = getattr(msg, "chat", None) if msg else None
        if chat is not None:
            return chat.id
        return event.from_user.id if event.from_user else None
    if isinstance(event, MessageReactionUpdated):
        return event.chat.id
    return None


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        text = getattr(event, "text", None) or ""
        if user and user.id in get_settings().admin_id_set:
            return await handler(event, data)
        if isinstance(event, Message) and str(text).startswith("/admin"):
            return await handler(event, data)
        if not await db.flag_on("maintenance"):
            return await handler(event, data)
        bot: Bot | None = data.get("bot")
        chat_id = _chat_id(event)
        if isinstance(event, CallbackQuery):
            try:
                await event.answer("Технические работы", show_alert=False)
            except Exception:
                pass
        if bot and chat_id:
            try:
                await notify_user(bot, chat_id)
            except Exception:
                try:
                    await bot.send_message(chat_id, await current_text(), parse_mode=None)
                except Exception:
                    pass
        return None
