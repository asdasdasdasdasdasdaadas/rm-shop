from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone

from app import db
from app.config import get_settings
from app.remnawave import RemnawaveClient, RemnawaveError, is_subscription_active

logger = logging.getLogger("rm-shop.sync")

_RESUME_KEY = "panel_sync_resume"


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


def _local_as_panel(local: dict | None) -> dict | None:
    if not local:
        return None
    if not (
        local.get("remnawave_id")
        or local.get("remnawave_uuid")
        or local.get("subscription_url")
        or local.get("expire_at")
        or local.get("panel_status")
        or local.get("last_synced_at")
    ):
        return None
    expire = local.get("expire_at")
    return {
        "id": local.get("remnawave_id"),
        "uuid": local.get("remnawave_uuid"),
        "status": local.get("panel_status"),
        "expireAt": expire.isoformat() if expire else None,
        "subscriptionUrl": local.get("subscription_url") or "",
    }


async def fetch_panel(
    rw: RemnawaveClient,
    telegram_id: int,
    *,
    force: bool = False,
    local: dict | None = None,
    allow_stale: bool = False,
) -> dict | None:
    if local is None:
        local = await db.get_user(telegram_id)
    snapshot = _local_as_panel(local)
    if not force:
        if snapshot and (_fresh(local) or allow_stale):
            return snapshot
        if allow_stale:
            return None
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


async def _load_resume() -> dict | None:
    raw = (await db.get_kv(_RESUME_KEY)).strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    if str(data.get("kind") or "") not in {"stream", "list"}:
        return None
    return data


async def _save_resume(resume: dict | None) -> None:
    if not resume or resume.get("kind") == "done":
        await db.set_kv(_RESUME_KEY, "")
        return
    await db.set_kv(_RESUME_KEY, json.dumps(resume, ensure_ascii=False, default=str))


async def _report_stale(rw: RemnawaveClient, started: float, pages: int) -> None:
    n = await _sync_stale_batch(rw)
    if n:
        logger.info("Список панели пуст или недоступен, сверка порцией: %s пользователей", n)
    elif pages == 0:
        logger.info("Панель не отдала список, сверка порцией: 0")
    await db.set_job_report(
        "panel_sync",
        {
            "mode": "по одному",
            "pages": pages,
            "seen": n,
            "applied": n,
            "seconds": round(time.monotonic() - started, 1),
            "partial": False,
        },
    )


async def sync_all(rw: RemnawaveClient) -> None:
    settings = get_settings()
    size = max(50, min(500, settings.panel_sync_page_size))
    budget = max(5, min(120, int(settings.panel_sync_tick_seconds)))
    started = time.monotonic()
    deadline = started + budget
    resume = await _load_resume()
    new_pass = resume is None
    pages = 0
    seen = 0
    applied = 0
    pending = resume
    prev = resume
    try:
        while time.monotonic() < deadline:
            prev = pending
            users, pending = await rw.next_users_page(pending, size)
            pages += 1
            seen += len(users)
            if users:
                applied += await db.apply_panel_snapshots(users)
            if (pending or {}).get("kind") == "done":
                break
            if not users:
                pending = prev
                break
    except RemnawaveError:
        if pages == 0:
            logger.warning("Пакетная сверка с панелью недоступна, берём порцию по одному")
            await _save_resume(resume)
            await _report_stale(rw, started, 0)
            return
        logger.warning("Сверка оборвалась, продолжим с той же страницы в следующем цикле")
        pending = prev
    if new_pass and seen == 0:
        await _save_resume(None)
        await _report_stale(rw, started, pages)
        return
    done = (pending or {}).get("kind") == "done"
    await _save_resume(None if done else pending)
    mode = "пакет" if done else "пакет, часть"
    logger.info(
        "Сверка с Remnawave: %s, страниц %s, учёток %s, обновлено %s",
        mode,
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
            "partial": not done,
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
