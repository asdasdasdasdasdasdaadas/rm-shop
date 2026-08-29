from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import db
from app.config import get_settings
from app.remnawave import RemnawaveClient, RemnawaveError, is_subscription_active


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


async def fetch_panel(rw: RemnawaveClient, telegram_id: int, *, force: bool = False) -> dict | None:
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


async def sync_all(rw: RemnawaveClient) -> None:
    for telegram_id in await db.list_panel_telegram_ids():
        try:
            await fetch_panel(rw, telegram_id, force=True)
        except Exception:
            continue


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
