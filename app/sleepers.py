"""The panel cleanup: once a day, devices that never carried traffic panel_cleanup_days after being added are
removed from Remnawave and from the cabinet (each is its own panel user). Adding a device again takes a minute.
The very first cleanup waits FIRST_DELAY_DAYS after the feature arrived.
"""
from __future__ import annotations

import asyncio
import logging

from app import db
from app.config import get_settings

logger = logging.getLogger("rm-shop.sleepers")

CLEANUP_FROM_KEY = "panel_cleanup_from"
FIRST_DELAY_DAYS = 3


async def cleanup_panel(rw) -> int:
    """Remove never-online devices older than panel_cleanup_days from the panel and the cabinet."""
    s = get_settings()
    if not s.panel_cleanup_enabled:
        return 0
    # The first cleanup waits 3 days after this feature arrived.
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start = await db.get_kv(CLEANUP_FROM_KEY)
    if not start:
        await db.set_kv(CLEANUP_FROM_KEY, (now + timedelta(days=FIRST_DELAY_DAYS)).isoformat())
        return 0
    try:
        if now < datetime.fromisoformat(start):
            return 0
    except ValueError:
        pass
    from app.remnawave import RemnawaveError
    removed = 0
    for item in await db.never_online_devices(max(7, int(s.panel_cleanup_days))):
        if item.get("remnawave_id"):
            try:
                await rw.delete_panel_user(int(item["remnawave_id"]))
            except RemnawaveError:
                logger.warning("Чистка панели: устройство %s не удалилось", item["id"], exc_info=True)
                continue
        gone = await db.drop_never_online_device(int(item["id"]))
        if not gone:
            continue
        removed += 1
        await db.log_billing_event(int(gone["telegram_id"]), "device_delete", source="cleanup",
                                   device_id=int(gone["id"]), device_title=str(gone.get("title") or ""),
                                   note=f"Удалено: не подключалось {int(s.panel_cleanup_days)} дней")
    if removed:
        logger.info("Чистка панели: удалено устройств без подключения: %s", removed)
    return removed


async def cleanup_loop(rw) -> None:
    await asyncio.sleep(15 * 60)
    while True:
        try:
            while await cleanup_panel(rw) >= 50:  # a big first run goes in batches
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Чистка панели")
        await asyncio.sleep(24 * 60 * 60)
