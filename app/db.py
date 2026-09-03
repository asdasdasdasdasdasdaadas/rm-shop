from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import logging
import secrets

import asyncpg

from app.config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_pool: asyncpg.Pool | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(row: asyncpg.Record | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


async def init_db() -> None:
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    async with _pool.acquire() as conn:
        for stmt in schema.split(";"):
            chunk = stmt.strip()
            if chunk:
                await conn.execute(chunk)


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _pool_req() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("База не инициализирована")
    return _pool


async def upsert_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    referred_by: int | None = None,
) -> None:
    pool = _pool_req()
    ref = referred_by if referred_by and referred_by != telegram_id else None
    await pool.execute(
        """
        INSERT INTO users (telegram_id, username, first_name, referred_by)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (telegram_id) DO UPDATE SET
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name
        """,
        telegram_id,
        username,
        first_name,
        ref,
    )


async def get_user(telegram_id: int) -> dict | None:
    row = await _pool_req().fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
    return _as_dict(row)


async def claim_referral_reward(telegram_id: int) -> int | None:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET referral_rewarded = TRUE
        WHERE telegram_id = $1
          AND referred_by IS NOT NULL
          AND referral_rewarded = FALSE
        RETURNING referred_by
        """,
        telegram_id,
    )
    if not row:
        return None
    return int(row["referred_by"])


async def unclaim_referral_reward(telegram_id: int) -> None:
    await _pool_req().execute(
        "UPDATE users SET referral_rewarded = FALSE WHERE telegram_id = $1",
        telegram_id,
    )


async def start_story_check(telegram_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET story_pending_at = timezone('utc', now())
        WHERE telegram_id = $1
          AND story_rewarded_at IS NULL
          AND story_pending_at IS NULL
        RETURNING telegram_id
        """,
        telegram_id,
    )
    return bool(row)


async def approve_story_reward(telegram_id: int, amount: int) -> int | None:
    if amount <= 0:
        return None
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET story_rewarded_at = timezone('utc', now()),
            balance_rub = COALESCE(balance_rub, 0) + $2
        WHERE telegram_id = $1
          AND story_rewarded_at IS NULL
          AND story_pending_at IS NOT NULL
        RETURNING balance_rub
        """,
        telegram_id,
        amount,
    )
    if not row:
        return None
    return int(row["balance_rub"])


async def reject_story_check(telegram_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET story_pending_at = NULL
        WHERE telegram_id = $1
          AND story_rewarded_at IS NULL
          AND story_pending_at IS NOT NULL
        RETURNING telegram_id
        """,
        telegram_id,
    )
    return bool(row)


async def payout_due_story_rewards(minutes: int, amount: int) -> list[dict]:
    if minutes < 1 or amount <= 0:
        return []
    rows = await _pool_req().fetch(
        """
        UPDATE users
        SET story_rewarded_at = timezone('utc', now()),
            balance_rub = COALESCE(balance_rub, 0) + $2
        WHERE story_rewarded_at IS NULL
          AND story_pending_at IS NOT NULL
          AND story_pending_at <= timezone('utc', now()) - ($1::int * INTERVAL '1 minute')
        RETURNING telegram_id, balance_rub, first_name
        """,
        minutes,
        amount,
    )
    return [dict(r) for r in rows]


async def claim_story_reward(telegram_id: int, amount: int) -> int | None:
    if amount <= 0:
        return None
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET story_rewarded_at = timezone('utc', now()),
            balance_rub = COALESCE(balance_rub, 0) + $2
        WHERE telegram_id = $1
          AND story_rewarded_at IS NULL
        RETURNING balance_rub
        """,
        telegram_id,
        amount,
    )
    if not row:
        return None
    return int(row["balance_rub"])


async def accept_legal(telegram_id: int) -> None:
    await _pool_req().execute(
        "UPDATE users SET accepted_legal_at = $1 WHERE telegram_id = $2",
        _utc_now(),
        telegram_id,
    )


async def mark_trial_used(telegram_id: int, remnawave_id: int | None = None) -> None:
    if remnawave_id is not None:
        await _pool_req().execute(
            "UPDATE users SET trial_used = TRUE, remnawave_id = $1 WHERE telegram_id = $2",
            remnawave_id,
            telegram_id,
        )
    else:
        await _pool_req().execute(
            "UPDATE users SET trial_used = TRUE WHERE telegram_id = $1",
            telegram_id,
        )


async def save_panel_id(telegram_id: int, remnawave_id: int) -> None:
    await _pool_req().execute(
        "UPDATE users SET remnawave_id = $1 WHERE telegram_id = $2",
        remnawave_id,
        telegram_id,
    )


async def save_panel_snapshot(telegram_id: int, panel: dict | None) -> None:
    if not panel:
        await _pool_req().execute(
            "UPDATE users SET last_synced_at = $1 WHERE telegram_id = $2",
            _utc_now(),
            telegram_id,
        )
        return
    raw_id = panel.get("id")
    remnawave_id = None
    try:
        if raw_id is not None and str(raw_id).isdigit():
            remnawave_id = int(raw_id)
    except (TypeError, ValueError):
        remnawave_id = None
    uuid = str(panel.get("uuid") or "") or None
    expire_raw = panel.get("expireAt")
    expire_at = None
    if expire_raw:
        try:
            expire_at = datetime.fromisoformat(str(expire_raw).replace("Z", "+00:00"))
        except ValueError:
            expire_at = None
    await _pool_req().execute(
        """
        UPDATE users SET
            remnawave_id = COALESCE($2, remnawave_id),
            remnawave_uuid = COALESCE($3, remnawave_uuid),
            expire_at = $4,
            panel_status = $5,
            subscription_url = $6,
            last_synced_at = $7
        WHERE telegram_id = $1
        """,
        telegram_id,
        remnawave_id,
        uuid,
        expire_at,
        str(panel.get("status") or "") or None,
        panel.get("subscriptionUrl") or None,
        _utc_now(),
    )


def _panel_sync_tuple(panel: dict) -> tuple | None:
    raw_id = panel.get("id")
    remnawave_id = None
    try:
        if raw_id is not None and str(raw_id).isdigit():
            remnawave_id = int(raw_id)
    except (TypeError, ValueError):
        remnawave_id = None
    uuid = str(panel.get("uuid") or "") or None
    expire_raw = panel.get("expireAt")
    expire_at = None
    if expire_raw:
        try:
            expire_at = datetime.fromisoformat(str(expire_raw).replace("Z", "+00:00"))
        except ValueError:
            expire_at = None
    status = str(panel.get("status") or "") or None
    sub = panel.get("subscriptionUrl") or None
    online = None
    traffic = panel.get("userTraffic") if isinstance(panel.get("userTraffic"), dict) else {}
    nested = panel.get("traffic") if isinstance(panel.get("traffic"), dict) else {}
    for raw in (
        traffic.get("onlineAt"),
        nested.get("onlineAt"),
        panel.get("onlineAt"),
        panel.get("lastConnectedAt"),
        panel.get("lastOnlineAt"),
    ):
        if not raw:
            continue
        try:
            online = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            break
        except ValueError:
            online = None
    if remnawave_id is None and not uuid:
        return None
    return remnawave_id, uuid, expire_at, status, sub, online


async def apply_panel_snapshots(panels: list[dict]) -> int:
    rows = []
    seen: set[tuple] = set()
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        parsed = _panel_sync_tuple(panel)
        if not parsed:
            continue
        key = (parsed[0], parsed[1])
        if key in seen:
            continue
        seen.add(key)
        rows.append(parsed)
    if not rows:
        return 0
    ids = [r[0] for r in rows]
    uuids = [r[1] for r in rows]
    expires = [r[2] for r in rows]
    statuses = [r[3] for r in rows]
    subs = [r[4] for r in rows]
    onlines = [r[5] for r in rows]
    now = _utc_now()
    pool = _pool_req()
    await pool.execute(
        """
        UPDATE devices d SET
            remnawave_uuid = COALESCE(v.uuid, d.remnawave_uuid),
            subscription_url = COALESCE(v.sub, d.subscription_url),
            last_online_at = CASE
                WHEN v.online_at IS NULL THEN d.last_online_at
                WHEN d.last_online_at IS NULL OR v.online_at > d.last_online_at THEN v.online_at
                ELSE d.last_online_at
            END
        FROM unnest(
            $1::bigint[], $2::text[], $3::text[], $4::timestamptz[]
        ) AS v(pid, uuid, sub, online_at)
        WHERE d.remnawave_id IS NOT NULL AND d.remnawave_id = v.pid
        """,
        ids,
        uuids,
        subs,
        onlines,
    )
    result = await pool.execute(
        """
        UPDATE users u SET
            remnawave_uuid = COALESCE(v.uuid, u.remnawave_uuid),
            expire_at = v.expire_at,
            panel_status = v.status,
            subscription_url = COALESCE(v.sub, u.subscription_url),
            last_synced_at = $6
        FROM unnest(
            $1::bigint[], $2::text[], $3::timestamptz[], $4::text[], $5::text[]
        ) AS v(pid, uuid, expire_at, status, sub)
        WHERE u.remnawave_id IS NOT NULL AND u.remnawave_id = v.pid
        """,
        ids,
        uuids,
        expires,
        statuses,
        subs,
        now,
    )
    await pool.execute(
        """
        UPDATE users u SET
            remnawave_id = COALESCE(u.remnawave_id, v.pid),
            remnawave_uuid = COALESCE(v.uuid, u.remnawave_uuid),
            expire_at = v.expire_at,
            panel_status = v.status,
            subscription_url = COALESCE(v.sub, u.subscription_url),
            last_synced_at = $6
        FROM unnest(
            $1::bigint[], $2::text[], $3::timestamptz[], $4::text[], $5::text[]
        ) AS v(pid, uuid, expire_at, status, sub)
        WHERE COALESCE(u.remnawave_uuid, '') <> ''
          AND v.uuid IS NOT NULL
          AND u.remnawave_uuid = v.uuid
          AND (u.remnawave_id IS NULL OR u.remnawave_id = v.pid)
        """,
        ids,
        uuids,
        expires,
        statuses,
        subs,
        now,
    )
    try:
        return int(str(result).split()[-1])
    except (TypeError, ValueError, IndexError):
        return len(rows)


async def list_stale_panel_telegram_ids(limit: int) -> list[int]:
    rows = await _pool_req().fetch(
        """
        SELECT telegram_id FROM users
        WHERE remnawave_id IS NOT NULL OR COALESCE(remnawave_uuid, '') <> ''
        ORDER BY last_synced_at NULLS FIRST, telegram_id
        LIMIT $1
        """,
        limit,
    )
    return [int(r["telegram_id"]) for r in rows]


async def save_device_subscription(remnawave_id: int, panel: dict | None) -> str | None:
    if not panel:
        return None
    uuid = str(panel.get("uuid") or "") or None
    row = await _pool_req().fetchrow(
        """
        UPDATE devices SET
            remnawave_uuid = COALESCE($2, remnawave_uuid),
            subscription_url = $3
        WHERE remnawave_id = $1
        RETURNING title
        """,
        remnawave_id,
        uuid,
        panel.get("subscriptionUrl") or None,
    )
    return str(row["title"]) if row and row.get("title") else None


async def list_devices_for_users(telegram_ids: list[int]) -> list[dict]:
    if not telegram_ids:
        return []
    rows = await _pool_req().fetch(
        "SELECT * FROM devices WHERE telegram_id = ANY($1::bigint[]) ORDER BY id",
        telegram_ids,
    )
    return [dict(r) for r in rows]


async def set_device_last_online(device_id: int, online_at) -> None:
    await _pool_req().execute(
        "UPDATE devices SET last_online_at = $2 WHERE id = $1",
        device_id,
        online_at,
    )


async def list_panel_telegram_ids() -> list[int]:
    rows = await _pool_req().fetch(
        """
        SELECT telegram_id FROM users
        WHERE remnawave_id IS NOT NULL OR remnawave_uuid IS NOT NULL
        """
    )
    return [int(r["telegram_id"]) for r in rows]


async def list_panel_accounts() -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT telegram_id, remnawave_id, remnawave_uuid, NULL::text AS title
        FROM users
        WHERE remnawave_id IS NOT NULL OR COALESCE(remnawave_uuid, '') <> ''
        UNION ALL
        SELECT telegram_id, remnawave_id, NULL, title
        FROM devices
        WHERE remnawave_id IS NOT NULL
        """
    )
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        key = str(item.get("remnawave_id") or item.get("remnawave_uuid") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


async def save_payment(telegram_id: int, plan_code: str, stars: int, payment_id: str) -> bool:
    try:
        await _pool_req().execute(
            """
            INSERT INTO payments (telegram_id, plan_code, stars, telegram_payment_id)
            VALUES ($1, $2, $3, $4)
            """,
            telegram_id,
            plan_code,
            stars,
            payment_id,
        )
        return True
    except asyncpg.exceptions.UniqueViolationError:
        return False


async def add_balance_days(telegram_id: int, days: int) -> int:
    row = await _pool_req().fetchrow(
        """
        UPDATE users SET balance_days = COALESCE(balance_days, 0) + $2
        WHERE telegram_id = $1
        RETURNING balance_days
        """,
        telegram_id,
        days,
    )
    return int(row["balance_days"]) if row else 0


async def add_balance_rub(telegram_id: int, amount: int) -> int:
    if amount == 0:
        local = await get_user(telegram_id)
        return int((local or {}).get("balance_rub") or 0)
    row = await _pool_req().fetchrow(
        """
        UPDATE users SET balance_rub = COALESCE(balance_rub, 0) + $2
        WHERE telegram_id = $1
        RETURNING balance_rub
        """,
        telegram_id,
        amount,
    )
    return int(row["balance_rub"]) if row else 0


async def mark_paid_topup(telegram_id: int) -> None:
    await _pool_req().execute(
        "UPDATE users SET has_paid_topup = TRUE WHERE telegram_id = $1",
        telegram_id,
    )


async def flag_on(key: str) -> bool:
    val = await _pool_req().fetchval("SELECT value FROM app_flags WHERE key = $1", key)
    return str(val or "").lower() in {"1", "true", "on", "yes"}


async def set_flag(key: str, on: bool) -> None:
    await set_kv(key, "1" if on else "0")


async def get_kv(key: str) -> str:
    val = await _pool_req().fetchval("SELECT value FROM app_flags WHERE key = $1", key)
    return str(val or "")


async def set_kv(key: str, value: str) -> None:
    await _pool_req().execute(
        """
        INSERT INTO app_flags (key, value) VALUES ($1, $2)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """,
        key,
        value,
    )


async def get_flags() -> dict:
    rows = await _pool_req().fetch("SELECT key, value FROM app_flags")
    data = {str(r["key"]): str(r["value"] or "") for r in rows}

    def _on(key: str) -> bool:
        return data.get(key, "").lower() in {"1", "true", "on", "yes"}

    return {
        "maintenance": _on("maintenance"),
        "billing_paused": _on("billing_paused"),
        "trial_nudge": _on("trial_nudge"),
        "maintenance_notice": data.get("maintenance_notice") or "",
    }


async def set_job_report(name: str, payload: dict) -> None:
    data = dict(payload)
    data["at"] = _utc_now().isoformat()
    await set_kv(f"job:{name}", json.dumps(data, ensure_ascii=False, default=str))


async def get_job_report(name: str) -> dict | None:
    raw = (await get_kv(f"job:{name}")).strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


async def open_trust_loan(telegram_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        """
        SELECT * FROM trust_loans
        WHERE telegram_id = $1 AND collected_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        telegram_id,
    )
    return _as_dict(row)


async def take_trust_loan(telegram_id: int, credit: int, due_at, debt: int | None = None) -> dict:
    repay = int(debt if debt is not None else credit)
    row = await _pool_req().fetchrow(
        """
        INSERT INTO trust_loans (telegram_id, amount, due_at)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        telegram_id,
        repay,
        due_at,
    )
    await add_balance_rub(telegram_id, int(credit))
    return dict(row) if row else {"amount": repay, "due_at": due_at}


async def due_trust_loans() -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT * FROM trust_loans
        WHERE collected_at IS NULL AND due_at <= timezone('utc', now())
        ORDER BY id
        """
    )
    return [dict(r) for r in rows]


async def collect_trust_loan(loan_id: int, telegram_id: int, amount: int) -> None:
    await add_balance_rub(telegram_id, -abs(amount))
    await _pool_req().execute(
        "UPDATE trust_loans SET collected_at = timezone('utc', now()) WHERE id = $1 AND collected_at IS NULL",
        loan_id,
    )


async def user_is_blocked(telegram_id: int) -> bool:
    val = await _pool_req().fetchval(
        "SELECT blocked_at IS NOT NULL FROM users WHERE telegram_id = $1",
        telegram_id,
    )
    return bool(val)


async def set_user_blocked(telegram_id: int, blocked: bool, reason: str | None = None) -> bool:
    pool = _pool_req()
    if blocked:
        note = (reason or "").strip()[:500] or None
        result = await pool.execute(
            """
            UPDATE users
            SET blocked_at = COALESCE(blocked_at, $2),
                blocked_reason = $3
            WHERE telegram_id = $1
            """,
            telegram_id,
            _utc_now(),
            note,
        )
    else:
        result = await pool.execute(
            "UPDATE users SET blocked_at = NULL, blocked_reason = NULL WHERE telegram_id = $1",
            telegram_id,
        )
    return result == "UPDATE 1"


async def list_panel_ids_for_user(telegram_id: int) -> list[int]:
    local = await get_user(telegram_id)
    if not local:
        return []
    ids: list[int] = []
    if local.get("remnawave_id"):
        ids.append(int(local["remnawave_id"]))
    for item in await list_devices(telegram_id):
        if item.get("remnawave_id"):
            ids.append(int(item["remnawave_id"]))
    return list(dict.fromkeys(ids))


async def clear_device_billing(telegram_id: int) -> None:
    await _pool_req().execute(
        "UPDATE devices SET last_billed_on = NULL WHERE telegram_id = $1",
        telegram_id,
    )


async def delete_user(telegram_id: int) -> bool:
    pool = _pool_req()
    async with pool.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval("SELECT 1 FROM users WHERE telegram_id = $1", telegram_id)
            if not exists:
                return False
            await conn.execute("DELETE FROM trust_loans WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM vpn_reports WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM promo_uses WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM payments WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM rollypay_orders WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM cabinet_tokens WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM billing_events WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM devices WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM users WHERE telegram_id = $1", telegram_id)
    return True


async def spend_balance_rub(telegram_id: int, amount: int) -> bool:
    if amount < 1:
        return True
    row = await _pool_req().fetchrow(
        """
        UPDATE users SET balance_rub = balance_rub - $2
        WHERE telegram_id = $1 AND COALESCE(balance_rub, 0) >= $2
        RETURNING telegram_id
        """,
        telegram_id,
        amount,
    )
    return row is not None


async def spend_balance_day(telegram_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE users SET balance_days = balance_days - 1
        WHERE telegram_id = $1 AND balance_days >= 1
        RETURNING telegram_id
        """,
        telegram_id,
    )
    return row is not None


async def list_devices(telegram_id: int) -> list[dict]:
    rows = await _pool_req().fetch(
        "SELECT * FROM devices WHERE telegram_id = $1 ORDER BY id",
        telegram_id,
    )
    return [dict(r) for r in rows]


async def add_device(
    telegram_id: int,
    title: str,
    remnawave_id: int,
    platform: str | None = None,
    client: str | None = None,
) -> dict:
    row = await _pool_req().fetchrow(
        """
        INSERT INTO devices (telegram_id, title, remnawave_id, last_billed_on, platform, client)
        VALUES ($1, $2, $3, (timezone('utc', now()))::date, $4, $5)
        RETURNING *
        """,
        telegram_id,
        title,
        remnawave_id,
        platform,
        client,
    )
    return dict(row) if row else {"title": title, "remnawave_id": remnawave_id}


async def get_device(telegram_id: int, device_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        "SELECT * FROM devices WHERE id = $1 AND telegram_id = $2",
        device_id,
        telegram_id,
    )
    return _as_dict(row)


async def delete_device(telegram_id: int, device_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        "DELETE FROM devices WHERE id = $1 AND telegram_id = $2 RETURNING *",
        device_id,
        telegram_id,
    )
    return _as_dict(row)


async def device_count(telegram_id: int) -> int:
    val = await _pool_req().fetchval(
        "SELECT COUNT(*) FROM devices WHERE telegram_id = $1",
        telegram_id,
    )
    return int(val or 0)


async def devices_due_for_billing() -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT id, telegram_id, title, remnawave_id
        FROM devices
        WHERE remnawave_id IS NOT NULL
          AND (last_billed_on IS NULL OR last_billed_on < (timezone('utc', now()))::date)
          AND telegram_id NOT IN (SELECT telegram_id FROM users WHERE blocked_at IS NOT NULL)
        ORDER BY id
        """
    )
    return [dict(r) for r in rows]


async def devices_to_retry_disable() -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT d.id, d.telegram_id, d.title, d.remnawave_id
        FROM devices d
        WHERE d.remnawave_id IS NOT NULL
          AND d.telegram_id NOT IN (SELECT telegram_id FROM users WHERE blocked_at IS NOT NULL)
          AND EXISTS (
            SELECT 1
            FROM billing_events e
            WHERE e.device_id = d.id
              AND e.kind = 'error'
              AND COALESCE(e.note, '') = 'Панель не отключила устройство'
              AND e.created_at >= (timezone('utc', now()))::date
          )
          AND NOT EXISTS (
            SELECT 1
            FROM billing_events e
            WHERE e.device_id = d.id
              AND e.kind IN ('disable', 'charge', 'pause')
              AND e.created_at >= (timezone('utc', now()))::date
          )
        ORDER BY d.id
        """
    )
    return [dict(r) for r in rows]


async def mark_device_billed(device_id: int) -> None:
    await mark_devices_billed([device_id])


async def mark_devices_billed(device_ids: list[int]) -> None:
    ids = [int(x) for x in device_ids if x is not None]
    if not ids:
        return
    await _pool_req().execute(
        """
        UPDATE devices
        SET last_billed_on = (timezone('utc', now()))::date
        WHERE id = ANY($1::bigint[])
        """,
        ids,
    )


async def save_rollypay_order(
    order_id: str,
    telegram_id: int,
    plan_code: str,
    payment_id: str,
    pay_url: str,
) -> None:
    await _pool_req().execute(
        """
        INSERT INTO rollypay_orders (order_id, telegram_id, plan_code, payment_id, pay_url, status)
        VALUES ($1, $2, $3, $4, $5, 'created')
        """,
        order_id,
        telegram_id,
        plan_code,
        payment_id,
        pay_url,
    )


async def get_rollypay_order(order_id: str) -> dict | None:
    row = await _pool_req().fetchrow("SELECT * FROM rollypay_orders WHERE order_id = $1", order_id)
    return _as_dict(row)


async def get_rollypay_order_by_payment(payment_id: str) -> dict | None:
    row = await _pool_req().fetchrow("SELECT * FROM rollypay_orders WHERE payment_id = $1", payment_id)
    return _as_dict(row)


async def mark_rollypay_paid(order_id: str) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE rollypay_orders SET status = 'granted'
        WHERE order_id = $1 AND status <> 'granted'
        RETURNING order_id
        """,
        order_id,
    )
    return row is not None


async def use_promo(telegram_id: int, code: str) -> bool:
    try:
        await _pool_req().execute(
            "INSERT INTO promo_uses (telegram_id, code) VALUES ($1, $2)",
            telegram_id,
            code.upper(),
        )
        return True
    except asyncpg.exceptions.UniqueViolationError:
        return False


def _jsonable(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if hasattr(value, "isoformat"):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


async def admin_stats() -> dict:
    pool = _pool_req()
    users = await pool.fetchrow(
        """
        SELECT
            COUNT(*)::int AS users_total,
            COUNT(*) FILTER (WHERE accepted_legal_at IS NOT NULL)::int AS legal_ok,
            COUNT(*) FILTER (WHERE trial_used)::int AS trial_used,
            COUNT(*) FILTER (WHERE expire_at IS NOT NULL AND expire_at > NOW())::int AS active,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day')::int AS new_1d,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days')::int AS new_7d,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days')::int AS new_30d,
            COUNT(*) FILTER (WHERE referred_by IS NOT NULL)::int AS referred,
            COUNT(*) FILTER (WHERE referral_rewarded)::int AS referral_rewarded,
            COUNT(*) FILTER (WHERE blocked_at IS NOT NULL)::int AS blocked
        FROM users
        """
    )
    orders = await pool.fetch("SELECT status, COUNT(*)::int AS n FROM rollypay_orders GROUP BY status")
    plans = await pool.fetch(
        """
        SELECT plan_code, COUNT(*)::int AS n
        FROM rollypay_orders
        WHERE status = 'granted'
        GROUP BY plan_code
        """
    )
    promo = await pool.fetchval("SELECT COUNT(*)::int FROM promo_uses")
    stars = await pool.fetchval("SELECT COUNT(*)::int FROM payments")
    billing_today = await pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE kind = 'charge')::int AS charges,
            COUNT(*) FILTER (WHERE kind = 'error')::int AS errors,
            COALESCE(SUM(amount) FILTER (WHERE amount > 0), 0)::int AS credited
        FROM billing_events
        WHERE created_at >= ((CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Moscow')::date)
              AT TIME ZONE 'Europe/Moscow'
        """
    )
    broadcast_users = await pool.fetchval(
        "SELECT COUNT(*)::int FROM users WHERE blocked_at IS NULL"
    )
    return {
        "users": dict(users) if users else {},
        "orders": {r["status"]: r["n"] for r in orders},
        "plans": {r["plan_code"]: r["n"] for r in plans},
        "promo_uses": int(promo or 0),
        "stars_payments": int(stars or 0),
        "vpn_reports": int(await pool.fetchval("SELECT COUNT(*)::int FROM vpn_reports") or 0),
        "billing_today": dict(billing_today) if billing_today else {},
        "broadcast_users": int(broadcast_users or 0),
    }


def _admin_users_filter(query: str, extra: dict | None = None) -> tuple[str, list]:
    clauses: list[str] = []
    args: list = []
    q = (query or "").strip()
    extra = extra or {}
    if q.lower() in {"блок", "blocked", "ban"}:
        clauses.append("u.blocked_at IS NOT NULL")
    elif q:
        args.append(f"%{q}%")
        n = len(args)
        clauses.append(
            f"""(
            u.username ILIKE ${n} OR u.first_name ILIKE ${n} OR u.telegram_id::text LIKE ${n}
               OR u.referred_by::text LIKE ${n} OR ref.username ILIKE ${n} OR ref.first_name ILIKE ${n}
            )"""
        )
    status = str(extra.get("status") or "").strip()
    if status == "block":
        clauses.append("u.blocked_at IS NOT NULL")
    elif status == "ok":
        clauses.append("u.blocked_at IS NULL")
    trial = str(extra.get("trial") or "").strip()
    if trial == "yes":
        clauses.append("u.trial_used")
    elif trial == "no":
        clauses.append("NOT u.trial_used")
    devices = str(extra.get("devices") or "").strip()
    if devices == "yes":
        clauses.append("EXISTS (SELECT 1 FROM devices d0 WHERE d0.telegram_id = u.telegram_id)")
    elif devices == "no":
        clauses.append("NOT EXISTS (SELECT 1 FROM devices d0 WHERE d0.telegram_id = u.telegram_id)")
    for key, op in (("bal_min", ">="), ("bal_max", "<=")):
        raw = str(extra.get(key) or "").strip()
        if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
            args.append(int(raw))
            clauses.append(f"COALESCE(u.balance_rub, 0) {op} ${len(args)}")
    from_d = str(extra.get("from") or "").strip()
    to_d = str(extra.get("to") or "").strip()
    if from_d:
        args.append(from_d)
        clauses.append(f"u.created_at >= ${len(args)}::date")
    if to_d:
        args.append(to_d)
        clauses.append(f"u.created_at < (${len(args)}::date + INTERVAL '1 day')")
    if not clauses:
        return "", []
    return "WHERE " + " AND ".join(clauses), args


async def admin_list_users(
    query: str, limit: int, offset: int, extra: dict | None = None
) -> tuple[list[dict], int]:
    pool = _pool_req()
    where, args = _admin_users_filter(query, extra)
    total_sql = f"""
        SELECT COUNT(*)::int FROM users u
        LEFT JOIN users ref ON ref.telegram_id = u.referred_by
        {where}
    """
    list_sql = f"""
        SELECT u.*,
               ref.username AS referrer_username,
               ref.first_name AS referrer_name,
               (
                   SELECT COUNT(*)::int FROM devices d WHERE d.telegram_id = u.telegram_id
               ) AS device_count,
               (
                   SELECT COALESCE(string_agg(d.title, ', ' ORDER BY d.id), '')
                   FROM devices d
                   WHERE d.telegram_id = u.telegram_id
               ) AS device_titles,
               (
                   SELECT MAX(d.last_online_at)
                   FROM devices d
                   WHERE d.telegram_id = u.telegram_id
               ) AS last_online_at,
               (
                   SELECT COUNT(*)::int FROM users inv WHERE inv.referred_by = u.telegram_id
               ) AS invited_count
        FROM users u
        LEFT JOIN users ref ON ref.telegram_id = u.referred_by
        {where}
        ORDER BY u.created_at DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
    """
    total = await pool.fetchval(total_sql, *args)
    rows = await pool.fetch(list_sql, *args, limit, offset)
    return [_jsonable(dict(r)) for r in rows], int(total or 0)


async def admin_user_ids(query: str, limit: int, extra: dict | None = None) -> tuple[list[int], int]:
    pool = _pool_req()
    where, args = _admin_users_filter(query, extra)
    total = await pool.fetchval(
        f"""
        SELECT COUNT(*)::int FROM users u
        LEFT JOIN users ref ON ref.telegram_id = u.referred_by
        {where}
        """,
        *args,
    )
    rows = await pool.fetch(
        f"""
        SELECT u.telegram_id FROM users u
        LEFT JOIN users ref ON ref.telegram_id = u.referred_by
        {where}
        ORDER BY u.created_at DESC
        LIMIT ${len(args) + 1}
        """,
        *args,
        limit,
    )
    return [int(r["telegram_id"]) for r in rows], int(total or 0)


async def admin_list_referrals(
    query: str, limit: int, offset: int, extra: dict | None = None
) -> tuple[list[dict], int]:
    pool = _pool_req()
    extra = extra or {}
    q = query.strip()
    where = "WHERE u.referred_by IS NOT NULL"
    args: list = []
    if q:
        pattern = f"%{q}%"
        args.append(pattern)
        n = len(args)
        where += f"""
            AND (
                u.username ILIKE ${n} OR u.first_name ILIKE ${n} OR u.telegram_id::text LIKE ${n}
                OR r.username ILIKE ${n} OR r.first_name ILIKE ${n} OR r.telegram_id::text LIKE ${n}
            )
        """
    reward = str(extra.get("reward") or "").strip()
    if reward == "yes":
        where += " AND u.referral_rewarded"
    elif reward == "no":
        where += " AND NOT u.referral_rewarded"
    from_d = str(extra.get("from") or "").strip()
    to_d = str(extra.get("to") or "").strip()
    if from_d:
        args.append(from_d)
        where += f" AND u.created_at >= ${len(args)}::date"
    if to_d:
        args.append(to_d)
        where += f" AND u.created_at < (${len(args)}::date + INTERVAL '1 day')"
    total = await pool.fetchval(
        f"""
        SELECT COUNT(*)::int
        FROM users u
        JOIN users r ON r.telegram_id = u.referred_by
        {where}
        """,
        *args,
    )
    rows = await pool.fetch(
        f"""
        SELECT
            u.telegram_id AS invitee_id,
            u.username AS invitee_username,
            u.first_name AS invitee_name,
            u.created_at AS invitee_at,
            u.referral_rewarded,
            r.telegram_id AS referrer_id,
            r.username AS referrer_username,
            r.first_name AS referrer_name
        FROM users u
        JOIN users r ON r.telegram_id = u.referred_by
        {where}
        ORDER BY u.created_at DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args,
        limit,
        offset,
    )
    return [_jsonable(dict(r)) for r in rows], int(total or 0)


async def admin_list_orders(
    query: str, limit: int, offset: int, extra: dict | None = None
) -> tuple[list[dict], int]:
    pool = _pool_req()
    extra = extra or {}
    clauses: list[str] = []
    args: list = []
    q = query.strip()
    if q:
        args.append(f"%{q}%")
        n = len(args)
        clauses.append(
            f"""(order_id ILIKE ${n} OR COALESCE(payment_id, '') ILIKE ${n}
               OR telegram_id::text LIKE ${n} OR status ILIKE ${n}
               OR COALESCE(plan_code, '') ILIKE ${n})"""
        )
    status = str(extra.get("status") or "").strip()
    if status:
        args.append(status)
        clauses.append(f"status = ${len(args)}")
    from_d = str(extra.get("from") or "").strip()
    to_d = str(extra.get("to") or "").strip()
    if from_d:
        args.append(from_d)
        clauses.append(f"created_at >= ${len(args)}::date")
    if to_d:
        args.append(to_d)
        clauses.append(f"created_at < (${len(args)}::date + INTERVAL '1 day')")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = await pool.fetchval(f"SELECT COUNT(*)::int FROM rollypay_orders {where}", *args)
    n = len(args)
    rows = await pool.fetch(
        f"SELECT * FROM rollypay_orders {where} ORDER BY created_at DESC LIMIT ${n + 1} OFFSET ${n + 2}",
        *args,
        limit,
        offset,
    )
    return [_jsonable(dict(r)) for r in rows], int(total or 0)


async def reset_trial(telegram_id: int) -> bool:
    result = await _pool_req().execute(
        "UPDATE users SET trial_used = FALSE WHERE telegram_id = $1",
        telegram_id,
    )
    return result == "UPDATE 1"


async def claim_trial_nudge_batch(limit: int = 40) -> list[dict]:
    rows = await _pool_req().fetch(
        """
        WITH due AS (
            SELECT u.telegram_id
            FROM users u
            WHERE u.trial_nudge_sent_at IS NULL
              AND u.trial_used = FALSE
              AND u.blocked_at IS NULL
              AND u.remnawave_id IS NULL
              AND COALESCE(u.has_paid_topup, FALSE) = FALSE
              AND COALESCE(u.balance_rub, 0) = 0
              AND u.created_at <= timezone('utc', now()) - INTERVAL '24 hours'
              AND NOT EXISTS (
                  SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id
              )
            ORDER BY u.created_at
            LIMIT $1
        )
        UPDATE users AS u
        SET trial_nudge_sent_at = timezone('utc', now())
        FROM due
        WHERE u.telegram_id = due.telegram_id
          AND u.trial_nudge_sent_at IS NULL
        RETURNING u.telegram_id, u.first_name
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def list_broadcast_ids() -> list[int]:
    rows = await _pool_req().fetch(
        "SELECT telegram_id FROM users WHERE blocked_at IS NULL ORDER BY telegram_id"
    )
    return [int(r["telegram_id"]) for r in rows]


async def last_vpn_report_at(telegram_id: int):
    return await _pool_req().fetchval(
        "SELECT created_at FROM vpn_reports WHERE telegram_id = $1 ORDER BY created_at DESC LIMIT 1",
        telegram_id,
    )


async def count_vpn_reports_today() -> int:
    return int(
        await _pool_req().fetchval(
            """
            SELECT COUNT(*)::int
            FROM vpn_reports
            WHERE created_at >= (timezone('Europe/Moscow', now())::date)::timestamp
                  AT TIME ZONE 'Europe/Moscow'
            """
        )
        or 0
    )


async def save_vpn_report(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    expire_at,
    panel_status: str | None,
    subscription_url: str | None,
    remnawave_uuid: str | None,
    payload: dict | None = None,
) -> dict:
    row = await _pool_req().fetchrow(
        """
        INSERT INTO vpn_reports (
            telegram_id, username, first_name, expire_at, panel_status, subscription_url, remnawave_uuid, payload
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
        RETURNING *
        """,
        telegram_id,
        username,
        first_name,
        expire_at,
        panel_status,
        subscription_url,
        remnawave_uuid,
        json.dumps(payload or {}, ensure_ascii=False, default=str),
    )
    return _jsonable(dict(row)) if row else {}


def _cabinet_token_hash(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()


async def issue_cabinet_token(telegram_id: int, days: int = 10) -> str:
    raw = secrets.token_urlsafe(32)
    expires = _utc_now() + timedelta(days=max(1, days))
    await _pool_req().execute(
        """
        INSERT INTO cabinet_tokens (token_hash, telegram_id, expires_at)
        VALUES ($1, $2, $3)
        """,
        _cabinet_token_hash(raw),
        telegram_id,
        expires,
    )
    return raw


async def delete_cabinet_token(raw: str) -> None:
    await _pool_req().execute(
        "DELETE FROM cabinet_tokens WHERE token_hash = $1",
        _cabinet_token_hash(raw),
    )


async def get_cabinet_token_user(raw: str) -> int | None:
    token = (raw or "").strip()
    if not token:
        return None
    row = await _pool_req().fetchrow(
        """
        SELECT telegram_id FROM cabinet_tokens
        WHERE token_hash = $1 AND expires_at > NOW()
        """,
        _cabinet_token_hash(token),
    )
    if not row:
        return None
    return int(row["telegram_id"])


async def purge_expired_cabinet_tokens() -> None:
    await _pool_req().execute("DELETE FROM cabinet_tokens WHERE expires_at <= NOW()")


async def users_needing_cabinet_link(day_price: int) -> list[int]:
    price = max(1, int(day_price))
    rows = await _pool_req().fetch(
        """
        SELECT u.telegram_id
        FROM users u
        JOIN devices d ON d.telegram_id = u.telegram_id
        WHERE u.blocked_at IS NULL
        GROUP BY u.telegram_id, u.balance_rub
        HAVING COUNT(d.id) > 0
           AND COALESCE(u.balance_rub, 0) < (2 * $1 * COUNT(d.id))
           AND NOT EXISTS (
               SELECT 1 FROM cabinet_tokens t
               WHERE t.telegram_id = u.telegram_id
                 AND t.expires_at > NOW()
           )
        ORDER BY u.telegram_id
        """,
        price,
    )
    return [int(r["telegram_id"]) for r in rows]


async def log_billing_event(
    telegram_id: int,
    kind: str,
    *,
    source: str = "cron",
    amount: int = 0,
    balance_after: int | None = None,
    device_id: int | None = None,
    device_title: str | None = None,
    note: str | None = None,
) -> None:
    try:
        after = balance_after
        if after is None:
            local = await get_user(telegram_id)
            after = int((local or {}).get("balance_rub") or 0) if local else None
        await _pool_req().execute(
            """
            INSERT INTO billing_events (
                telegram_id, kind, source, amount, balance_after, device_id, device_title, note
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            telegram_id,
            kind,
            source,
            int(amount or 0),
            after,
            int(device_id) if device_id is not None else None,
            (device_title or "").strip() or None,
            (note or "").strip() or None,
        )
    except Exception:
        logging.getLogger("rm-shop.db").exception("Не удалось записать событие биллинга")


def _admin_billing_filter(
    query: str, telegram_id: int | None = None, extra: dict | None = None
) -> tuple[str, list]:
    args: list = []
    clauses: list[str] = []
    extra = extra or {}
    if telegram_id is not None:
        args.append(int(telegram_id))
        clauses.append(f"e.telegram_id = ${len(args)}")
    q = (query or "").strip()
    if q:
        args.append(f"%{q}%")
        n = len(args)
        clauses.append(
            f"""(
               e.telegram_id::text LIKE ${n}
               OR e.kind ILIKE ${n}
               OR e.source ILIKE ${n}
               OR COALESCE(e.device_title, '') ILIKE ${n}
               OR COALESCE(e.note, '') ILIKE ${n}
               OR COALESCE(u.username, '') ILIKE ${n}
               OR COALESCE(u.first_name, '') ILIKE ${n}
            )"""
        )
    kind = str(extra.get("kind") or "").strip()
    if kind:
        args.append(kind)
        clauses.append(f"e.kind = ${len(args)}")
    source = str(extra.get("source") or "").strip()
    if source:
        args.append(source)
        clauses.append(f"e.source = ${len(args)}")
    from_d = str(extra.get("from") or "").strip()
    to_d = str(extra.get("to") or "").strip()
    if from_d:
        args.append(from_d)
        clauses.append(f"e.created_at >= ${len(args)}::date")
    if to_d:
        args.append(to_d)
        clauses.append(f"e.created_at < (${len(args)}::date + INTERVAL '1 day')")
    if not clauses:
        return "", []
    return "WHERE " + " AND ".join(clauses), args


async def admin_list_billing(
    query: str,
    limit: int,
    offset: int,
    telegram_id: int | None = None,
    extra: dict | None = None,
) -> tuple[list[dict], int]:
    pool = _pool_req()
    where, args = _admin_billing_filter(query, telegram_id, extra)
    total = await pool.fetchval(
        f"""
        SELECT COUNT(*)::int
        FROM billing_events e
        LEFT JOIN users u ON u.telegram_id = e.telegram_id
        {where}
        """,
        *args,
    )
    n = len(args)
    rows = await pool.fetch(
        f"""
        SELECT e.*, u.username, u.first_name
        FROM billing_events e
        LEFT JOIN users u ON u.telegram_id = e.telegram_id
        {where}
        ORDER BY e.id DESC
        LIMIT ${n + 1} OFFSET ${n + 2}
        """,
        *args,
        limit,
        offset,
    )
    return [_jsonable(dict(r)) for r in rows], int(total or 0)


async def admin_list_reports(
    limit: int, offset: int, extra: dict | None = None
) -> tuple[list[dict], int]:
    pool = _pool_req()
    extra = extra or {}
    clauses: list[str] = []
    args: list = []
    status = str(extra.get("status") or "").strip()
    if status == "empty":
        clauses.append("(panel_status IS NULL OR panel_status = '')")
    elif status:
        args.append(status)
        clauses.append(f"panel_status = ${len(args)}")
    from_d = str(extra.get("from") or "").strip()
    to_d = str(extra.get("to") or "").strip()
    if from_d:
        args.append(from_d)
        clauses.append(f"created_at >= ${len(args)}::date")
    if to_d:
        args.append(to_d)
        clauses.append(f"created_at < (${len(args)}::date + INTERVAL '1 day')")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = await pool.fetchval(f"SELECT COUNT(*)::int FROM vpn_reports {where}", *args)
    n = len(args)
    rows = await pool.fetch(
        f"SELECT * FROM vpn_reports {where} ORDER BY created_at DESC LIMIT ${n + 1} OFFSET ${n + 2}",
        *args,
        limit,
        offset,
    )
    return [_jsonable(dict(r)) for r in rows], int(total or 0)
