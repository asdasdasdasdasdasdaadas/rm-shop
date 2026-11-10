"""Photo, GIF or video attached to an admin broadcast.

The admin uploads the file once; it is kept in data/broadcast. The first delivery uploads it to Telegram,
every later one reuses the returned file_id, so a broadcast to thousands of users sends the bytes once.
"""
from __future__ import annotations

import re
import time
import uuid
from pathlib import Path

from app.config import ROOT

MEDIA_DIR = ROOT / "data" / "broadcast"
KINDS = ("photo", "animation", "video")
CAPTION_LIMIT = 1024
PHOTO_MAX = 10 * 1024 * 1024
MAX_BYTES = 50 * 1024 * 1024  # Bot API upload limit
KEEP_DAYS = 90
STORED_RE = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp|gif|mp4|mov|webm)$")
KIND_LABEL = {"photo": "фото", "animation": "GIF", "video": "видео"}


def _ext(data: bytes, filename: str) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:6] in {b"GIF87a", b"GIF89a"}:
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[4:8] == b"ftyp":
        return "mov" if data[8:10] == b"qt" else "mp4"
    if data[:4] == b"\x1aE\xdf\xa3":
        return "webm"
    raise ValueError("Нужен файл JPG, PNG, WEBP, GIF, MP4, MOV или WEBM")


def kind_for(ext: str, as_gif: bool = False) -> str:
    """GIF goes out as an animation; a video can too, then it loops silently like a GIF in the chat."""
    if ext == "gif":
        return "animation"
    if ext in {"mp4", "mov", "webm"}:
        return "animation" if as_gif else "video"
    return "photo"


def _prune(now: float) -> None:
    for path in MEDIA_DIR.glob("*"):
        try:
            if path.is_file() and now - path.stat().st_mtime > KEEP_DAYS * 86400:
                path.unlink()
        except OSError:
            pass


def store(data: bytes, filename: str = "", as_gif: bool = False) -> dict:
    if not data:
        raise ValueError("Пустой файл")
    if len(data) > MAX_BYTES:
        raise ValueError("Файл больше 50 МБ — Telegram не примет его от бота")
    ext = _ext(data, filename)
    kind = kind_for(ext, as_gif)
    if kind == "photo" and len(data) > PHOTO_MAX:
        raise ValueError("Фото больше 10 МБ — Telegram не примет его от бота")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    _prune(time.time())
    stored = f"{uuid.uuid4().hex}.{ext}"
    (MEDIA_DIR / stored).write_bytes(data)
    return {"id": stored, "kind": kind, "size": len(data), "name": Path(filename or stored).name[:120]}


def path_of(media_id: str) -> Path | None:
    name = str(media_id or "")
    if not STORED_RE.match(name):
        return None
    path = MEDIA_DIR / name
    return path if path.is_file() else None


def check(raw) -> tuple[dict | None, str | None]:
    """The {id, kind} from a broadcast request; (None, None) when nothing is attached."""
    if not raw:
        return None, None
    if not isinstance(raw, dict):
        return None, "Некорректное вложение"
    media_id, kind = str(raw.get("id") or ""), str(raw.get("kind") or "")
    if kind not in KINDS:
        return None, "Неизвестный тип вложения"
    if path_of(media_id) is None:
        return None, "Файл рассылки не найден, загрузите его снова"
    ext = media_id.rsplit(".", 1)[1]
    if kind == "photo" and ext not in {"jpg", "png", "webp"}:
        return None, "Это не фото"
    if kind != "photo" and ext in {"jpg", "png", "webp"}:
        return None, "Картинку можно отправить только как фото"
    return {"id": media_id, "kind": kind}, None


def _file_id(message, kind: str) -> str | None:
    if kind == "photo":
        sizes = getattr(message, "photo", None) or []
        return sizes[-1].file_id if sizes else None
    item = getattr(message, kind, None) or getattr(message, "document", None)
    return getattr(item, "file_id", None)


async def send(bot, chat_id: int, media: dict, caption: str, markup, cache: dict | None = None):
    """Send the attachment with the text as its caption; `cache` keeps the Telegram file_id between recipients."""
    from aiogram.types import FSInputFile

    kind = media["kind"]
    cache = cache if cache is not None else {}
    source = cache.get(media["id"])
    if source is None:
        path = path_of(media["id"])
        if path is None:
            raise RuntimeError("Файл рассылки пропал с диска")
        source = FSInputFile(path)
    caption = caption or None
    if kind == "photo":
        message = await bot.send_photo(chat_id, source, caption=caption, reply_markup=markup)
    elif kind == "animation":
        message = await bot.send_animation(chat_id, source, caption=caption, reply_markup=markup)
    else:
        message = await bot.send_video(chat_id, source, caption=caption, reply_markup=markup, supports_streaming=True)
    file_id = _file_id(message, kind)
    if file_id and media["id"] not in cache:
        cache[media["id"]] = file_id
    return message
