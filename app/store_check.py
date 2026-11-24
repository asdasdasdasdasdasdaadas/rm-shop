"""Can the VPN app still be downloaded? Checked in advance, so /connect never sends people to a removed app.

Apps vanish from the Russian App Store and from Google Play often. Every few hours every link of
the cabinet's apps — store and direct download — is asked:
  App Store — the iTunes lookup for the Russian storefront (country=ru): no result means not in RU;
  Google Play — the app page: 404 means gone (Google answers for the country the server is in);
  anything else (GitHub releases, an APK, a site) — the link itself: 404/410 means gone.
A failed request keeps the last known answer.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

import aiohttp

from app import db

logger = logging.getLogger(__name__)

KV_KEY = "store_check"
EVERY_SECONDS = 6 * 3600
_APPLE = re.compile(r"apps\.apple\.com/.*?\bid(\d+)")
_PLAY = re.compile(r"play\.google\.com/store/apps/details\?(?:.*&)?id=([\w.]+)")


def parse(url: str) -> tuple[str, str] | None:
    url = str(url or "")
    m = _APPLE.search(url)
    if m:
        return "appstore", m.group(1)
    m = _PLAY.search(url)
    if m:
        return "play", m.group(1)
    return None


async def check(http: aiohttp.ClientSession, url: str) -> bool | None:
    """True — downloadable, False — gone, None — not a web link, or nobody answered."""
    url = str(url or "")
    if not url.startswith(("https://", "http://")):
        return None
    kind = parse(url)
    try:
        if not kind:
            # One byte is enough: an APK link should not download the whole file.
            async with http.get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True) as r:
                if r.status in (404, 410):
                    return False
                return True if r.status in (200, 206) else None
        store, ident = kind
        if store == "appstore":
            async with http.get("https://itunes.apple.com/lookup", params={"id": ident, "country": "ru"}) as r:
                if r.status != 200:
                    return None
                data = json.loads(await r.text())
                return int(data.get("resultCount") or 0) > 0
        async with http.get("https://play.google.com/store/apps/details", params={"id": ident, "hl": "ru", "gl": "RU"}) as r:
            if r.status == 404:
                return False
            return True if r.status == 200 else None
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        logger.debug("Магазин не ответил про %s", url, exc_info=True)
        return None


def _all_urls(apps: list[dict]) -> set[str]:
    return {u for a in apps for key in ("stores", "direct") for u in (a.get(key) or {}).values()
            if str(u or "").startswith(("https://", "http://"))}


async def status() -> dict[str, dict]:
    """{store url: {"ok": bool, "at": iso}} from the last checks."""
    try:
        raw = await db.get_kv(KV_KEY)
        got = json.loads(raw) if raw else {}
        return got if isinstance(got, dict) else {}
    except Exception:
        logger.debug("Проверка магазинов: не прочитали", exc_info=True)
        return {}


async def refresh(http: aiohttp.ClientSession | None = None) -> dict[str, dict]:
    from app.vpn_apps import public_vpn_apps
    known = await status()
    urls = _all_urls(public_vpn_apps())
    own = http is None
    if own:
        http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20), headers={"User-Agent": "Mozilla/5.0"})
    try:
        out = {}
        for url in sorted(urls):
            ok = await check(http, url)
            if ok is None:
                if url in known:
                    out[url] = known[url]
                continue
            out[url] = {"ok": ok, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if url in known and known[url].get("ok") != ok:
                logger.warning("Магазин: %s теперь %s", url, "доступно" if ok else "недоступно")
    finally:
        if own:
            await http.close()
    await db.set_kv(KV_KEY, json.dumps(out, ensure_ascii=False))
    return out


def mark(apps: list[dict], checked: dict[str, dict]) -> list[dict]:
    """Each app gets `unavailable`: the platforms whose store link was found gone; a dead direct link is dropped."""
    dead = lambda u: (checked.get(u) or {}).get("ok") is False  # noqa: E731
    out = []
    for a in apps:
        b = dict(a)
        gone = sorted(p for p, u in (a.get("stores") or {}).items() if dead(u))
        if gone:
            b["unavailable"] = gone
        if a.get("direct") and any(dead(u) for u in a["direct"].values()):
            b["direct"] = {p: u for p, u in a["direct"].items() if not dead(u)}
        out.append(b)
    return out


async def loop() -> None:
    while True:
        try:
            await refresh()
        except Exception:
            logger.exception("Проверка магазинов не прошла")
        await asyncio.sleep(EVERY_SECONDS)
