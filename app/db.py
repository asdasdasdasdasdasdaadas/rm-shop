from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

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


async def list_panel_telegram_ids() -> list[int]:
    rows = await _pool_req().fetch(
        """
        SELECT telegram_id FROM users
        WHERE remnawave_id IS NOT NULL OR remnawave_uuid IS NOT NULL
        """
    )
    return [int(r["telegram_id"]) for r in rows]


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
    await _pool_req().execute(
        """
        INSERT INTO app_flags (key, value) VALUES ($1, $2)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """,
        key,
        "1" if on else "0",
    )


async def get_flags() -> dict[str, bool]:
    rows = await _pool_req().fetch("SELECT key, value FROM app_flags")
    data = {r["key"]: str(r["value"] or "").lower() in {"1", "true", "on", "yes"} for r in rows}
    return {
        "maintenance": bool(data.get("maintenance")),
        "billing_paused": bool(data.get("billing_paused")),
    }


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


async def take_trust_loan(telegram_id: int, amount: int, due_at) -> dict:
    row = await _pool_req().fetchrow(
        """
        INSERT INTO trust_loans (telegram_id, amount, due_at)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        telegram_id,
        amount,
        due_at,
    )
    await add_balance_rub(telegram_id, amount)
    return dict(row) if row else {"amount": amount, "due_at": due_at}


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
        ORDER BY id
        """
    )
    return [dict(r) for r in rows]


async def mark_device_billed(device_id: int) -> None:
    await _pool_req().execute(
        "UPDATE devices SET last_billed_on = (timezone('utc', now()))::date WHERE id = $1",
        device_id,
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
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days')::int AS new_30d
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
    return {
        "users": dict(users) if users else {},
        "orders": {r["status"]: r["n"] for r in orders},
        "plans": {r["plan_code"]: r["n"] for r in plans},
        "promo_uses": int(promo or 0),
        "stars_payments": int(stars or 0),
        "vpn_reports": int(await pool.fetchval("SELECT COUNT(*)::int FROM vpn_reports") or 0),
    }


async def admin_list_users(query: str, limit: int, offset: int) -> tuple[list[dict], int]:
    pool = _pool_req()
    q = query.strip()
    if q:
        pattern = f"%{q}%"
        total = await pool.fetchval(
            """
            SELECT COUNT(*)::int FROM users
            WHERE username ILIKE $1 OR first_name ILIKE $1 OR telegram_id::text LIKE $1
            """,
            pattern,
        )
        rows = await pool.fetch(
            """
            SELECT * FROM users
            WHERE username ILIKE $1 OR first_name ILIKE $1 OR telegram_id::text LIKE $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            pattern,
            limit,
            offset,
        )
    else:
        total = await pool.fetchval("SELECT COUNT(*)::int FROM users")
        rows = await pool.fetch(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
    return [_jsonable(dict(r)) for r in rows], int(total or 0)


async def admin_list_orders(query: str, limit: int, offset: int) -> tuple[list[dict], int]:
    pool = _pool_req()
    q = query.strip()
    if q:
        pattern = f"%{q}%"
        total = await pool.fetchval(
            """
            SELECT COUNT(*)::int FROM rollypay_orders
            WHERE order_id ILIKE $1 OR COALESCE(payment_id, '') ILIKE $1
               OR telegram_id::text LIKE $1 OR status ILIKE $1
            """,
            pattern,
        )
        rows = await pool.fetch(
            """
            SELECT * FROM rollypay_orders
            WHERE order_id ILIKE $1 OR COALESCE(payment_id, '') ILIKE $1
               OR telegram_id::text LIKE $1 OR status ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            pattern,
            limit,
            offset,
        )
    else:
        total = await pool.fetchval("SELECT COUNT(*)::int FROM rollypay_orders")
        rows = await pool.fetch(
            "SELECT * FROM rollypay_orders ORDER BY created_at DESC LIMIT $1 OFFSET $2",
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


async def list_broadcast_ids() -> list[int]:
    rows = await _pool_req().fetch("SELECT telegram_id FROM users ORDER BY telegram_id")
    return [int(r["telegram_id"]) for r in rows]


async def last_vpn_report_at(telegram_id: int):
    return await _pool_req().fetchval(
        "SELECT created_at FROM vpn_reports WHERE telegram_id = $1 ORDER BY created_at DESC LIMIT 1",
        telegram_id,
    )


async def save_vpn_report(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    expire_at,
    panel_status: str | None,
    subscription_url: str | None,
    remnawave_uuid: str | None,
) -> dict:
    row = await _pool_req().fetchrow(
        """
        INSERT INTO vpn_reports (
            telegram_id, username, first_name, expire_at, panel_status, subscription_url, remnawave_uuid
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        telegram_id,
        username,
        first_name,
        expire_at,
        panel_status,
        subscription_url,
        remnawave_uuid,
    )
    return _jsonable(dict(row)) if row else {}


async def admin_list_reports(limit: int, offset: int) -> tuple[list[dict], int]:
    pool = _pool_req()
    total = await pool.fetchval("SELECT COUNT(*)::int FROM vpn_reports")
    rows = await pool.fetch(
        "SELECT * FROM vpn_reports ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        limit,
        offset,
    )
    return [_jsonable(dict(r)) for r in rows], int(total or 0)
