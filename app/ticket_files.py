from __future__ import annotations

import hashlib
import hmac
import re
import time
import uuid
from pathlib import Path

from app.config import ROOT, get_settings

TICKET_DIR = ROOT / "data" / "tickets"
MAX_BYTES = 8 * 1024 * 1024
MAX_FILES = 5
TOKEN_TTL = 48 * 3600
STORED_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.[a-z0-9]{1,8}$")

_PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_VIDEO_EXTS = {".mp4", ".mov", ".webm"}
_DOC_EXTS = {".pdf", ".zip", ".txt"}
ALLOWED_EXTS = _PHOTO_EXTS | _VIDEO_EXTS | _DOC_EXTS

_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".txt": "text/plain",
}


def _secret() -> bytes:
    return hashlib.sha256(get_settings().bot_token.encode("utf-8")).digest()


def _ext_from_name(filename: str) -> str:
    name = (filename or "").rsplit(".", 1)
    if len(name) != 2:
        return ""
    ext = "." + name[1].lower()
    if ext == ".jpeg":
        return ".jpg"
    return ext if ext in ALLOWED_EXTS else ""


def _ext_from_bytes(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:6] in {b"GIF87a", b"GIF89a"}:
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:4] == b"%PDF":
        return ".pdf"
    if data[:4] == b"PK\x03\x04":
        return ".zip"
    if data[4:8] == b"ftyp":
        return ".mp4"
    if data[:4] == b"\x1aE\xdf\xa3":
        return ".webm"
    return None


def _kind_for(ext: str) -> str:
    if ext in _PHOTO_EXTS:
        return "photo"
    if ext in _VIDEO_EXTS:
        return "video"
    return "file"


def safe_original_name(filename: str, ext: str) -> str:
    raw = Path(filename or "").name.replace("\x00", "")
    raw = re.sub(r"[^\w.\- ()\[\]]+", "_", raw, flags=re.UNICODE).strip("._")
    if not raw:
        raw = "file" + ext
    if not raw.lower().endswith(ext):
        raw = raw[:80] + ext
    return raw[:120]


def inspect(data: bytes, filename: str = "", mime: str = "") -> dict:
    if not data:
        raise ValueError("Пустой файл")
    if len(data) > MAX_BYTES:
        raise ValueError("Файл больше 8 МБ")
    ext = _ext_from_bytes(data)
    name_ext = _ext_from_name(filename)
    if ext == ".zip" and name_ext and name_ext != ".zip":
        raise ValueError("Нужен файл JPG, PNG, WEBP, GIF, PDF, ZIP, TXT, MP4, MOV или WEBM")
    ext = ext or name_ext
    if ext not in ALLOWED_EXTS:
        raise ValueError("Нужен файл JPG, PNG, WEBP, GIF, PDF, ZIP, TXT, MP4, MOV или WEBM")
    kind = _kind_for(ext)
    return {
        "ext": ext,
        "kind": kind,
        "mime": _MIME.get(ext) or (mime or "application/octet-stream"),
        "original_name": safe_original_name(filename, ext),
        "size_bytes": len(data),
    }


def store_bytes(data: bytes, filename: str = "", mime: str = "") -> dict:
    meta = inspect(data, filename, mime)
    TICKET_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4()}{meta['ext']}"
    path = TICKET_DIR / stored
    path.write_bytes(data)
    return {
        "stored_name": stored,
        "original_name": meta["original_name"],
        "mime": meta["mime"],
        "kind": meta["kind"],
        "size_bytes": meta["size_bytes"],
    }


def unlink_stored(stored_name: str) -> None:
    path = stored_path(stored_name)
    if path:
        try:
            path.unlink()
        except OSError:
            pass


def stored_path(stored_name: str) -> Path | None:
    name = str(stored_name or "")
    if not STORED_RE.match(name):
        return None
    path = (TICKET_DIR / name).resolve()
    try:
        path.relative_to(TICKET_DIR.resolve())
    except ValueError:
        return None
    if not path.is_file():
        return None
    return path


def sign_file(att_id: int) -> str:
    exp = int(time.time()) + TOKEN_TTL
    raw = f"{int(att_id)}:{exp}"
    sig = hmac.new(_secret(), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return f"{exp}.{sig}"


def file_token_ok(att_id: int, token: str) -> bool:
    if not token or "." not in token:
        return False
    exp_s, sig = token.split(".", 1)
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    if exp < int(time.time()):
        return False
    raw = f"{int(att_id)}:{exp}"
    expected = hmac.new(_secret(), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(expected, sig)


def user_file_url(att_id: int) -> str:
    return f"/api/tickets/files/{int(att_id)}?t={sign_file(att_id)}"


def public_attachment(row: dict, *, for_admin: bool) -> dict:
    att_id = int(row["id"])
    return {
        "id": att_id,
        "original_name": row.get("original_name") or "",
        "mime": row.get("mime") or "",
        "kind": row.get("kind") or "file",
        "size_bytes": int(row.get("size_bytes") or 0),
        "url": (
            f"/admin/api/tickets/files/{att_id}"
            if for_admin
            else user_file_url(att_id)
        ),
    }
