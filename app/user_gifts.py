"""Gifts a user shows on their Telegram profile, and a rough wealth rating from them, for the admin user card.

Only gifts the user keeps visible on the profile are returned by Telegram (getUserGifts); hidden ones are not.
There is no market price in the Bot API, so the rating is an estimate: regular gifts count at their price
in Stars, collectible (NFT) gifts at a fixed amount scaled by the rarity of their model.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from aiogram.methods import GetUserGifts

from app import db

logger = logging.getLogger(__name__)

CACHE_SECONDS = 6 * 3600
MAX_PAGES = 3  # up to 300 gifts: enough for a rating, cheap on the Bot API
NFT_STARS = 2500  # a common collectible gift, roughly what one resells for in Stars

LEVELS = (  # (points from, label)
    (30000, "Очень богатый"),
    (7500, "Богатый"),
    (1500, "Состоятельный"),
    (300, "Средний"),
    (1, "Скромный"),
)


def rarity_factor(per_mille: int | None) -> int:
    """Rarer models are worth more: ≤0.5% ×6, ≤1.5% ×3, ≤3% ×2, the rest ×1."""
    p = int(per_mille or 1000)
    if p <= 5:
        return 6
    if p <= 15:
        return 3
    if p <= 30:
        return 2
    return 1


def _hex(color: int | None) -> str | None:
    return f"#{int(color) & 0xFFFFFF:06x}" if color is not None else None


def _thumb(sticker) -> str | None:
    """A file the admin page can show as an image: the sticker's preview, or the sticker itself when it is static."""
    if sticker is None:
        return None
    if getattr(sticker, "thumbnail", None):
        return sticker.thumbnail.file_id
    if not (getattr(sticker, "is_animated", False) or getattr(sticker, "is_video", False)):
        return sticker.file_id
    return None


def simplify(owned) -> dict[str, Any] | None:
    gift = getattr(owned, "gift", None)
    if gift is None:
        return None
    if getattr(owned, "type", "") == "unique":
        model, backdrop = gift.model, gift.backdrop
        colors = getattr(backdrop, "colors", None)
        return {
            "kind": "unique",
            "title": f"{gift.base_name} #{gift.number}",
            "slug": gift.name,
            "model": model.name,
            "rarity_per_mille": int(model.rarity_per_mille or 0),
            "rarity": getattr(model, "rarity", None),
            "backdrop": getattr(backdrop, "name", None),
            "center": _hex(getattr(colors, "center_color", None)),
            "edge": _hex(getattr(colors, "edge_color", None)),
            "symbol": getattr(gift.symbol, "name", None),
            "thumb": _thumb(model.sticker),
            "burned": bool(getattr(gift, "is_burned", False)),
            "blockchain": bool(getattr(gift, "is_from_blockchain", False)),
            "date": int(owned.send_date or 0),
        }
    return {
        "kind": "regular",
        "title": getattr(gift.sticker, "emoji", None) or "Подарок",
        "stars": int(gift.star_count or 0),
        "limited": gift.total_count is not None,
        "thumb": _thumb(gift.sticker),
        "date": int(owned.send_date or 0),
    }


def summarize(gifts: list[dict[str, Any]], total: int | None = None) -> dict[str, Any]:
    regular = [g for g in gifts if g["kind"] == "regular"]
    unique = [g for g in gifts if g["kind"] == "unique" and not g.get("burned")]
    stars = sum(g.get("stars") or 0 for g in regular)
    nft_points = sum(NFT_STARS * rarity_factor(g.get("rarity_per_mille")) for g in unique)
    points = stars + nft_points
    level, label = 0, "Нет подарков в профиле"
    for i, (start, name) in enumerate(LEVELS):
        if points >= start:
            level, label = len(LEVELS) - i, name
            break
    return {
        "level": level,
        "label": label,
        "points": points,
        "regular_count": len(regular),
        "regular_stars": stars,
        "unique_count": len(unique),
        "rare_count": sum(1 for g in unique if rarity_factor(g.get("rarity_per_mille")) > 1),
        "total": int(total if total is not None else len(gifts)),
    }


async def fetch(bot, telegram_id: int) -> tuple[list[dict[str, Any]], int]:
    gifts: list[dict[str, Any]] = []
    offset, total = "", 0
    for _ in range(MAX_PAGES):
        page = await bot(GetUserGifts(user_id=int(telegram_id), sort_by_price=True, offset=offset, limit=100))
        total = int(page.total_count or 0)
        gifts.extend(g for g in (simplify(item) for item in page.gifts) if g)
        offset = page.next_offset or ""
        if not offset:
            break
    return gifts, total


async def _cached(telegram_id: int) -> dict | None:
    row = await db._pool_req().fetchrow(
        "SELECT data, EXTRACT(EPOCH FROM fetched_at)::bigint AS at FROM user_gifts WHERE telegram_id=$1", int(telegram_id))
    if not row:
        return None
    data = row["data"]
    data = json.loads(data) if isinstance(data, str) else dict(data)
    data["fetched_at"] = int(row["at"])
    return data


async def _store(telegram_id: int, data: dict) -> None:
    summary = data["summary"]
    await db._pool_req().execute(
        """INSERT INTO user_gifts (telegram_id, data, level, points, fetched_at) VALUES ($1, $2::jsonb, $3, $4, NOW())
           ON CONFLICT (telegram_id) DO UPDATE SET data=EXCLUDED.data, level=EXCLUDED.level,
               points=EXCLUDED.points, fetched_at=NOW()""",
        int(telegram_id), json.dumps(data, ensure_ascii=False), int(summary["level"]), int(summary["points"]))


async def user_gifts(bot, telegram_id: int, *, refresh: bool = False) -> dict[str, Any]:
    """Cached for a few hours; `refresh` asks Telegram again. Errors come back with the last known data."""
    cached = await _cached(telegram_id)
    if cached and not refresh and time.time() - cached["fetched_at"] < CACHE_SECONDS:
        return cached
    if bot is None:
        return cached or {"gifts": [], "summary": summarize([]), "error": "Бот не запущен"}
    try:
        gifts, total = await fetch(bot, telegram_id)
    except Exception as exc:
        logger.info("Подарки пользователя %s не получены: %s", telegram_id, exc)
        error = getattr(exc, "message", None) or str(exc) or type(exc).__name__
        out = cached or {"gifts": [], "summary": summarize([])}
        return {**out, "error": f"Telegram не отдал подарки: {error}"}
    data = {"gifts": gifts, "summary": summarize(gifts, total)}
    await _store(telegram_id, data)
    data["fetched_at"] = int(time.time())
    return data
