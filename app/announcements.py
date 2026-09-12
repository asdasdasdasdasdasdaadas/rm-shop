from __future__ import annotations

import re
from pathlib import Path

from app.config import ROOT

PHOTO_DIR = ROOT / "data" / "announcements"
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PHOTO_MAX = 10 * 1024 * 1024
_SPACES = re.compile(r"[ \t]{2,}")

DEFAULT_KICKER = "Что нового"
DEFAULT_TITLE = "Мы кое-что обновили"
DEFAULT_LEAD = (
    "{hello} Появилось несколько удобств. "
    "Коротко расскажем, что изменилось, чтобы Вам было проще пользоваться сервисом."
)
DEFAULT_CLOSING = (
    "Если что-то будет непонятно, напишите в поддержку. "
    "Мы рядом и спокойно разберёмся."
)


def fill_placeholders(text: str, first_name: str | None) -> str:
    name = str(first_name or "").strip()
    hello = f"Здравствуйте, {name}." if name else "Здравствуйте."
    out = str(text or "")
    out = out.replace("{hello}", hello)
    out = out.replace("{name}", name or "друг")
    out = _SPACES.sub(" ", out)
    return out.strip()


def format_announcement_body(
    *,
    kicker: str = "",
    title: str = "",
    lead: str = "",
    items: list[str] | None = None,
    closing: str = "",
) -> str:
    lines: list[str] = []
    kick = str(kicker or "").strip()
    head = str(title or "").strip()
    intro = str(lead or "").strip()
    foot = str(closing or "").strip()
    if kick:
        lines.append(kick)
        lines.append("")
    if head:
        lines.append(head)
    if intro:
        if lines:
            lines.append("")
        lines.append(intro)
    cleaned = [str(x).strip() for x in (items or []) if str(x).strip()]
    if cleaned:
        if lines:
            lines.append("")
        lines.extend(f"- {item}" for item in cleaned)
    if foot:
        if lines:
            lines.append("")
        lines.append(foot)
    return "\n".join(lines).strip()


def render_announcement_body(
    *,
    kicker: str = "",
    title: str = "",
    lead: str = "",
    items: list[str] | None = None,
    closing: str = "",
    first_name: str | None = None,
    body: str | None = None,
) -> str:
    raw = body if body else format_announcement_body(
        kicker=kicker,
        title=title,
        lead=lead,
        items=items,
        closing=closing,
    )
    return fill_placeholders(raw, first_name)


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


def content_type_for(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "application/octet-stream")


def announcement_photo_path(image_name: str | None) -> Path | None:
    raw = str(image_name or "").strip()
    if not raw or "/" in raw or "\\" in raw or ".." in raw:
        return None
    path = PHOTO_DIR / raw
    if not path.is_file() or path.suffix.lower() not in PHOTO_EXTS:
        return None
    return path


def validate_announcement_photo(data: bytes, filename: str) -> str:
    if not data:
        raise ValueError("Прикрепите изображение")
    if len(data) > PHOTO_MAX:
        raise ValueError("Картинка больше 10 МБ")
    ext = _ext_from_bytes(data) or _ext_from_name(filename)
    if ext not in PHOTO_EXTS:
        raise ValueError("Нужен файл JPG, PNG, WEBP или GIF")
    return ext


def save_announcement_photo(ann_id: int, data: bytes, filename: str) -> str:
    ext = validate_announcement_photo(data, filename)
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{int(ann_id)}{ext}"
    path = PHOTO_DIR / name
    for old in PHOTO_DIR.glob(f"{int(ann_id)}.*"):
        if old != path:
            try:
                old.unlink()
            except OSError:
                pass
    path.write_bytes(data)
    return name
