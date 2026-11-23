"""Telegram Ads statistics, tied to our ad links.

Every ad in Telegram Ads promotes a URL; ours look like https://t.me/<bot>?start=ad_<slug>, the same slug as an
ad link in «Рост». Every 30 minutes (and on «Обновить») the bot reads all ads of the account
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
SYNC_SECONDS = 600         # the autobid needs fresh views: every 10 minutes
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
            page = await _call(client, token, "getAdsList", limit=100, return_target=True,
                               **({"offset": offset} if offset else {})) or {}
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
    try:
        await sync_stats(ads)
    except Exception:
        logger.warning("Статистика объявлений по 5 минут не обновилась", exc_info=True)
    report = {"ok": True, "at": datetime.now(timezone.utc).isoformat(), "ads": len(ads), "matched": matched,
              "currency": currency, "rate": float(rate) if rate else None,
              "remaining": account.get("remaining_budget"), "spent": account.get("spent_budget")}
    await db.set_job_report("tg_ads", report)
    return report


def token() -> str:
    return (get_settings().tg_ads_token or "").strip()


async def call(method: str, **params):
    """One Ads API call with the token from the settings; TgAdsError when it fails or there is no token."""
    tok = token()
    if not tok:
        raise TgAdsError("Не задан токен: Настройки → Telegram Ads")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            return await _call(client, tok, method, **params)
        except httpx.HTTPError as exc:
            raise TgAdsError(f"{method}: {exc}") from exc


STAT_STEP = 300
BACKFILL = 3 * 86400       # 1000 intervals of 5 minutes is the API limit; three days are enough for the cabinet


async def sync_stats(ads: list[dict], now: int | None = None) -> int:
    """Views, clicks and spend per 5 minutes of every ad that can still move: from the last stored interval
    (the last one is re-read, it was still filling up) or three days back for a new ad."""
    pool = db._pool_req()
    now = int(now or datetime.now(timezone.utc).timestamp())
    last = {int(r["ad_id"]): int(r["ts"].timestamp()) for r in await pool.fetch(
        "SELECT ad_id, MAX(ts) AS ts FROM tg_ad_stats GROUP BY ad_id")}
    stored = 0
    for ad in ads:
        try:
            ad_id = int(ad.get("ad_id"))
        except (TypeError, ValueError):
            continue
        status = str(ad.get("status") or "")
        if ad_id in last and status not in {"active", "on_hold"} and now - last[ad_id] > 2 * 3600:
            continue   # stopped, declined or in review for a while: nothing new to read
        start = last.get(ad_id, now - BACKFILL)
        start = max(start - start % STAT_STEP, now - BACKFILL)
        items = await call("getAdStats", ad_id=ad_id, from_time=start, to_time=now + STAT_STEP, interval=STAT_STEP) or []
        rows = [(ad_id, datetime.fromtimestamp(int(i["from_time"]), timezone.utc), int(i.get("views") or 0),
                 int(i.get("clicks") or 0), int(i.get("actions") or i.get("joins") or 0),
                 Decimal(str(i.get("spent_budget") or 0))) for i in items if str(i.get("from_time") or "").isdigit()]
        if rows:
            await pool.executemany(
                """INSERT INTO tg_ad_stats (ad_id, ts, views, clicks, actions, spent) VALUES ($1,$2,$3,$4,$5,$6)
                   ON CONFLICT (ad_id, ts) DO UPDATE SET views=EXCLUDED.views, clicks=EXCLUDED.clicks,
                       actions=EXCLUDED.actions, spent=EXCLUDED.spent""", rows)
            stored += len(rows)
        await asyncio.sleep(0.2)
    await pool.execute("DELETE FROM tg_ad_stats WHERE ts < NOW() - INTERVAL '120 days'")
    return stored


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
                else:
                    from app import tg_autobid
                    await tg_autobid.tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Синхронизация Telegram Ads")
        await asyncio.sleep(SYNC_SECONDS)
