"""Telegram Ads statistics, tied to our ad links.

Every ad in Telegram Ads promotes a URL; ours look like https://t.me/<bot>?start=ad_<slug>, the same slug as an
ad link in «Источники трафика». Every 30 minutes (and on «Обновить») the bot reads all ads of the account
(promoteapi.telegram.org/getAdsList, token in Настройки → Telegram Ads or TG_ADS_TOKEN in .env) and stores per ad: views, clicks,
conversions, spend in the account currency and in rubles. The links page then shows, next to who came and who paid,
what Telegram counted and what it cost — without typing the spend by hand.

Rubles: the account is in TON, EUR or Stars. tg_ads_rub_rate (₽ for one unit, in Настройки) wins when set;
otherwise a TON account uses the market TON price, and EUR/Stars stay without rubles until the rate is set.
The whole spend of an ad is converted at the rate of the latest sync.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import httpx

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.tg-ads")

API = "https://promoteapi.telegram.org"
SYNC_SECONDS = 1800
SLUG_RE = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")


class TgAdsError(RuntimeError):
    pass


def slug_from_url(url: str | None) -> str | None:
    """`ad_<slug>` from the start parameter of a t.me bot link, as the bot reads it in /start."""
    raw = str(url or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "https://" + raw
    try:
        query = parse_qs(urlparse(raw).query)
    except ValueError:
        return None
    start = (query.get("start") or [""])[0].strip()
    if not start.startswith("ad_"):
        return None
    slug = start[3:].lower()
    return slug if SLUG_RE.fullmatch(slug) and 2 <= len(slug) <= 32 else None


async def _call(client: httpx.AsyncClient, token: str, method: str, **params):
    r = await client.post(f"{API}/{method}", json=params, headers={"Authorization": f"Bearer {token}"})
    try:
        data = r.json()
    except ValueError:
        raise TgAdsError(f"{method}: ответ не JSON (HTTP {r.status_code})")
    if not data.get("ok"):
        raise TgAdsError(f"{method}: {data.get('error') or f'HTTP {r.status_code}'}")
    return data.get("result")


async def _rate(currency: str) -> Decimal | None:
    manual = int(get_settings().tg_ads_rub_rate or 0)
    if manual > 0:
        return Decimal(manual)
    if currency == "TON":
        try:
            from app.ton import rub_per_ton
            return await rub_per_ton()
        except Exception:
            logger.warning("Курс TON не получен, расход в рублях не обновлён", exc_info=True)
    return None


async def sync(client: httpx.AsyncClient | None = None) -> dict:
    """Read every ad of the account and store it. Returns a short report (also kept for the admin)."""
    token = (get_settings().tg_ads_token or "").strip()
    if not token:
        return {"ok": False, "error": "Не задан токен: Настройки → Telegram Ads"}
    own = client is None
    client = client or httpx.AsyncClient(timeout=20)
    try:
        account = await _call(client, token, "getCurrentAccount") or {}
        currency = str(account.get("currency") or "TON")
        ads, offset = [], None
        for _ in range(50):
            page = await _call(client, token, "getAdsList", limit=100, **({"offset": offset} if offset else {})) or {}
            ads += page.get("ads") or []
            offset = page.get("next_offset")
            if not offset:
                break
    except (TgAdsError, httpx.HTTPError) as exc:
        report = {"ok": False, "error": str(exc)[:300], "at": datetime.now(timezone.utc).isoformat()}
        await db.set_job_report("tg_ads", report)
        return report
    finally:
        if own:
            await client.aclose()
    rate = await _rate(currency)
    matched = await db.save_tg_ads(ads, currency, rate, slug_from_url)
    report = {"ok": True, "at": datetime.now(timezone.utc).isoformat(), "ads": len(ads), "matched": matched,
              "currency": currency, "rate": float(rate) if rate else None,
              "remaining": account.get("remaining_budget"), "spent": account.get("spent_budget")}
    await db.set_job_report("tg_ads", report)
    return report


_lock = asyncio.Lock()


async def sync_locked() -> dict:
    async with _lock:
        return await sync()


async def tg_ads_loop() -> None:
    await asyncio.sleep(90)
    while True:
        try:
            if (get_settings().tg_ads_token or "").strip():
                report = await sync_locked()
                if not report.get("ok"):
                    logger.warning("Telegram Ads: %s", report.get("error"))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Синхронизация Telegram Ads")
        await asyncio.sleep(SYNC_SECONDS)
