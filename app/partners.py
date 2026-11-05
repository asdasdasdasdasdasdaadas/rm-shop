"""Advertiser pages: a secret token in the URL opens one advertiser's links and their stats.

Anyone holding the link can add ad links for that advertiser; nobody can delete them there.
"""

from __future__ import annotations

import re
import secrets

from aiohttp import web

from app import db
from app.config import ROOT, get_settings

PAGE = ROOT / "webapp" / "partner.html"
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
MAX_LINKS = 100
_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow",
}


def _title(raw) -> str:
    name = str(raw or "").strip()
    if len(name) < 2:
        raise ValueError("Укажите название")
    if len(name) > 80:
        raise ValueError("Название слишком длинное")
    return name


def bot_link(slug: str) -> str:
    return f"https://t.me/{get_settings().bot_username}?start=ad_{slug}"


async def create_partner(title) -> dict:
    row = await db._pool_req().fetchrow(
        "INSERT INTO ad_partners (title, token) VALUES ($1, $2) RETURNING id, title, token, created_at, revoked_at",
        _title(title),
        secrets.token_urlsafe(24),
    )
    return dict(row)


async def revoke_partner(partner_id: int) -> bool:
    row = await db._pool_req().fetchrow(
        """
        UPDATE ad_partners SET revoked_at = timezone('utc', now())
        WHERE id = $1 AND revoked_at IS NULL
        RETURNING id
        """,
        int(partner_id),
    )
    return bool(row)


async def list_partners() -> list[dict]:
    rows = await db._pool_req().fetch(
        """
        SELECT p.id, p.title, p.token, p.created_at, p.revoked_at,
               COUNT(DISTINCT l.id) FILTER (WHERE l.archived_at IS NULL)::int AS links,
               COALESCE(SUM(l.clicks) FILTER (WHERE l.archived_at IS NULL), 0)::int AS clicks,
               (SELECT COUNT(*) FROM users u JOIN ad_links x ON x.id = u.ad_link_id
                 WHERE x.partner_id = p.id)::int AS users
        FROM ad_partners p
        LEFT JOIN ad_links l ON l.partner_id = p.id
        GROUP BY p.id
        ORDER BY p.revoked_at IS NOT NULL, p.created_at DESC
        """
    )
    return [dict(r) for r in rows]


async def partner_by_token(token: str) -> dict | None:
    if not TOKEN_RE.fullmatch(token or ""):
        return None
    row = await db._pool_req().fetchrow(
        "SELECT id, title FROM ad_partners WHERE token = $1 AND revoked_at IS NULL",
        token,
    )
    return dict(row) if row else None


def link_public(row: dict) -> dict:
    slug = str(row.get("slug") or "")
    return {
        "id": int(row["id"]),
        "title": row.get("title") or "",
        "url": bot_link(slug),
        "clicks": int(row.get("clicks") or 0),
        "users": int(row.get("users") or 0),
        "connected": int(row.get("connected") or 0),
        "paid": int(row.get("paid") or 0),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


async def _partner_or_404(request: web.Request) -> dict:
    partner = await partner_by_token(request.match_info.get("token", ""))
    if not partner:
        raise web.HTTPNotFound(text="Ссылка недействительна", headers=_HEADERS)
    return partner


async def page(request: web.Request) -> web.FileResponse:
    await _partner_or_404(request)
    return web.FileResponse(PAGE, headers=_HEADERS)


async def api(request: web.Request) -> web.Response:
    partner = await _partner_or_404(request)
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
        try:
            title = _title(body.get("title") if isinstance(body, dict) else "")
            active = await db.list_ad_links(partner_id=partner["id"])
            if len(active) >= MAX_LINKS:
                raise ValueError(f"Можно создать не больше {MAX_LINKS} ссылок")
            await db.create_ad_link(title, kind="manual", partner_id=partner["id"])
        except ValueError as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400, headers=_HEADERS)
    items = [link_public(r) for r in await db.list_ad_links(partner_id=partner["id"])]
    return web.json_response(
        {"ok": True, "brand": get_settings().brand_name, "title": partner["title"], "items": items},
        headers=_HEADERS,
    )


def mount_partners(app: web.Application) -> None:
    app.router.add_get("/partner/{token}", page)
    app.router.add_get("/partner/{token}/api", api)
    app.router.add_post("/partner/{token}/api", api)
