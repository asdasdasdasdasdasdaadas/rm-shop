from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from app import db
from app.config import get_settings
from app.remnawave import RemnawaveClient, RemnawaveError, is_subscription_active

logger = logging.getLogger("rm-shop.sync")


def _fresh(local: dict | None) -> bool:
    if not local or not local.get("last_synced_at"):
        return False
    ts = local["last_synced_at"]
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - ts
        return age <= timedelta(seconds=get_settings().panel_sync_ttl)
    return False


async def fetch_panel(
    rw: RemnawaveClient, telegram_id: int, *, force: bool = False, local: dict | None = None
) -> dict | None:
    if local is None:
        local = await db.get_user(telegram_id)
    if not force and _fresh(local) and (local.get("remnawave_id") or local.get("subscription_url")):
        return {
            "id": local.get("remnawave_id"),
            "uuid": local.get("remnawave_uuid"),
            "status": local.get("panel_status"),
            "expireAt": local["expire_at"].isoformat() if local.get("expire_at") else None,
            "subscriptionUrl": local.get("subscription_url") or "",
        }
    panel = None
    try:
        if local and local.get("remnawave_id") is not None:
            panel = await rw.get_user_by_id(int(local["remnawave_id"]))
        if not panel and local and local.get("remnawave_uuid"):
            panel = await rw.get_user_by_id(str(local["remnawave_uuid"]))
        if not panel:
            panel = await rw.get_user_by_telegram(telegram_id)
    except RemnawaveError:
        panel = None
    await db.save_panel_snapshot(telegram_id, panel)
    return panel


async def _sync_stale_batch(rw: RemnawaveClient) -> int:
    settings = get_settings()
    ids = await db.list_stale_panel_telegram_ids(max(1, settings.panel_sync_fallback_batch))
    if not ids:
        return 0
    sem = asyncio.Semaphore(max(1, settings.panel_sync_concurrency))

    async def one(telegram_id: int) -> None:
        async with sem:
            try:
                await fetch_panel(rw, telegram_id, force=True)
            except Exception:
                logger.debug("Не удалось сверить %s", telegram_id)

    await asyncio.gather(*[one(tid) for tid in ids])
    return len(ids)


async def sync_all(rw: RemnawaveClient) -> None:
    settings = get_settings()
    size = max(50, min(500, settings.panel_sync_page_size))
    started = time.monotonic()
    pages = 0
    seen = 0
    applied = 0
    mode = "пакет"
    try:
        async for users in rw.iter_user_pages(size):
            pages += 1
            seen += len(users)
            if users:
                applied += await db.apply_panel_snapshots(users)
    except RemnawaveError:
        logger.warning("Пакетная сверка с панелью недоступна, берём порцию по одному")
        n = await _sync_stale_batch(rw)
        logger.info("Сверка порцией: %s пользователей", n)
        await db.set_job_report(
            "panel_sync",
            {
                "mode": "по одному",
                "pages": 0,
                "seen": n,
                "applied": n,
                "seconds": round(time.monotonic() - started, 1),
            },
        )
        return
    if pages == 0 or seen == 0:
        n = await _sync_stale_batch(rw)
        mode = "по одному"
        if n:
            logger.info("Список панели пуст или недоступен, сверка порцией: %s пользователей", n)
        elif pages == 0:
            logger.info("Панель не отдала список, сверка порцией: 0")
        await db.set_job_report(
            "panel_sync",
            {
                "mode": mode,
                "pages": pages,
                "seen": n,
                "applied": n,
                "seconds": round(time.monotonic() - started, 1),
            },
        )
        return
    logger.info(
        "Сверка с Remnawave: %s страниц, %s учёток в панели, обновлено записей: %s",
        pages,
        seen,
        applied,
    )
    await db.set_job_report(
        "panel_sync",
        {
            "mode": mode,
            "pages": pages,
            "seen": seen,
            "applied": applied,
            "seconds": round(time.monotonic() - started, 1),
        },
    )


def has_access(local: dict | None, panel: dict | None) -> bool:
    if local and (local.get("trial_used") or local.get("remnawave_id") or local.get("remnawave_uuid")):
        if is_subscription_active(panel):
            return True
        expire = local.get("expire_at")
        if isinstance(expire, datetime):
            if expire.tzinfo is None:
                expire = expire.replace(tzinfo=timezone.utc)
            if expire > datetime.now(timezone.utc):
                return True
        return bool(local.get("trial_used") or local.get("remnawave_id") or local.get("subscription_url"))
    return is_subscription_active(panel)
