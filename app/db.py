from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import logging
import re
import secrets

import asyncpg

from app.config import get_settings
from app.tg_err import is_user_blocked_bot
from app.remnawave import panel_lifetime_traffic_bytes, panel_online_at, panel_used_traffic_bytes

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
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=max(20, int(settings.billing_concurrency) + 8),
    )
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    async with _pool.acquire() as conn:
        for stmt in schema.split(";"):
            chunk = stmt.strip()
            if chunk:
                await conn.execute(chunk)
    await _ensure_nudge_defaults()


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def _ensure_nudge_defaults() -> None:
    if (await get_kv("nudge_defaults_v2")) != "1":
        for key in ("trial_nudge", "invite_nudge", "info_nudge"):
            await set_flag(key, True)
        await set_kv("nudge_defaults_v2", "1")
    if (await get_kv("nudge_defaults_v4")) != "1":
        await set_flag("story_nudge", True)
        await _pool_req().execute(
            """
            UPDATE users u
            SET story_nudge_sent_at = NULL
            WHERE u.story_nudge_sent_at IS NOT NULL
              AND u.story_rewarded_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM message_log m
                  WHERE m.telegram_id = u.telegram_id
                    AND m.kind = 'nudge_story'
                    AND m.status = 'sent'
              )
            """
        )
        await set_kv("nudge_defaults_v4", "1")
        await set_kv("nudge_defaults_v3", "1")
    if (await get_kv("nudge_defaults_v5")) != "1":
        await _pool_req().execute(
            """
            UPDATE users
            SET story_nudge_sent_at = NULL
            WHERE story_nudge_sent_at IS NOT NULL
              AND story_rewarded_at IS NULL
              AND story_pending_at IS NULL
              AND first_online_at IS NULL
            """
        )
        await set_kv("nudge_defaults_v5", "1")
    if (await get_kv("welcome_intro_backfill")) != "1":
        await _pool_req().execute(
            """
            UPDATE users
            SET welcome_intro_sent_at = COALESCE(created_at, timezone('utc', now()))
            WHERE welcome_intro_sent_at IS NULL
            """
        )
        await set_kv("welcome_intro_backfill", "1")


def _pool_req() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("База не инициализирована")
    return _pool


async def upsert_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    referred_by: int | None = None,
    ad_link_id: int | None = None,
) -> dict | None:
    pool = _pool_req()
    ref = referred_by if referred_by and referred_by != telegram_id else None
    ad_id = int(ad_link_id) if ad_link_id else None
    row = await pool.fetchrow(
        """
        WITH before AS (
            SELECT referred_by FROM users WHERE telegram_id = $1
        ),
        upsert AS (
            INSERT INTO users (telegram_id, username, first_name, referred_by, ad_link_id)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                referred_by = CASE
                    WHEN users.referred_by IS NOT NULL THEN users.referred_by
                    WHEN EXCLUDED.referred_by IS NULL THEN users.referred_by
                    WHEN users.referral_rewarded
                      OR COALESCE(users.has_paid_topup, FALSE)
                      OR users.remnawave_id IS NOT NULL
                      OR EXISTS (
                          SELECT 1 FROM devices d WHERE d.telegram_id = users.telegram_id
                      )
                    THEN users.referred_by
                    ELSE EXCLUDED.referred_by
                END,
                ad_link_id = COALESCE(users.ad_link_id, EXCLUDED.ad_link_id),
                bot_blocked_at = NULL
            RETURNING telegram_id, username, first_name, referred_by
        )
        SELECT
            u.telegram_id,
            u.username,
            u.first_name,
            u.referred_by,
            (b.referred_by IS NULL AND u.referred_by IS NOT NULL) AS referral_attached
        FROM upsert u
        LEFT JOIN before b ON TRUE
        """,
        telegram_id,
        username,
        first_name,
        ref,
        ad_id,
    )
    return _as_dict(row)


async def get_user(telegram_id: int) -> dict | None:
    row = await _pool_req().fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
    return _as_dict(row)


async def claim_first_online(telegram_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET first_online_at = timezone('utc', now())
        WHERE telegram_id = $1
          AND first_online_at IS NULL
        RETURNING telegram_id, username, first_name
        """,
        telegram_id,
    )
    return _as_dict(row)


async def claim_first_online_for_panel_ids(panel_ids: list[int]) -> list[dict]:
    if not panel_ids:
        return []
    rows = await _pool_req().fetch(
        """
        UPDATE users u
        SET first_online_at = timezone('utc', now())
        WHERE u.first_online_at IS NULL
          AND (
              u.remnawave_id = ANY($1::bigint[])
              OR EXISTS (
                  SELECT 1
                  FROM devices d
                  WHERE d.telegram_id = u.telegram_id
                    AND d.remnawave_id = ANY($1::bigint[])
                    AND d.last_online_at IS NOT NULL
              )
          )
        RETURNING u.telegram_id, u.username, u.first_name
        """,
        panel_ids,
    )
    return [dict(r) for r in rows]


_AD_SLUG_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_AD_RU = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
        "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
        "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
        "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
        "я": "ya",
    }
)


def normalize_ad_slug(raw: str, *, title: str = "") -> str:
    text = (raw or "").strip().lower().replace(" ", "_")
    if text.startswith("ad_"):
        text = text[3:]
    if not text:
        text = (title or "").strip().lower().translate(_AD_RU)
        text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if not text or not _AD_SLUG_RE.fullmatch(text) or len(text) > 32:
        text = "ad" + secrets.token_hex(3)
    return text[:32]


async def touch_ad_link(slug: str) -> int | None:
    clean = (slug or "").strip().lower()
    if not _AD_SLUG_RE.fullmatch(clean):
        return None
    row = await _pool_req().fetchrow(
        """
        UPDATE ad_links
        SET clicks = COALESCE(clicks, 0) + 1
        WHERE slug = $1
        RETURNING id
        """,
        clean,
    )
    return int(row["id"]) if row else None


async def create_ad_link(title: str, slug: str = "") -> dict:
    name = str(title or "").strip()
    if len(name) < 2:
        raise ValueError("Укажите название ссылки")
    if len(name) > 80:
        raise ValueError("Название слишком длинное")
    raw_slug = str(slug or "").strip()
    if raw_slug:
        candidate = raw_slug.lower()
        if candidate.startswith("ad_"):
            candidate = candidate[3:]
        candidate = candidate.replace(" ", "_")
        if not _AD_SLUG_RE.fullmatch(candidate) or not (2 <= len(candidate) <= 32):
            raise ValueError("Код: латиница, цифры и подчёркивание, от 2 до 32 знаков")
        base = candidate
    else:
        base = normalize_ad_slug("", title=name)
    pool = _pool_req()
    for i in range(8):
        candidate = base if i == 0 else f"{base[:24]}_{secrets.token_hex(2)}"
        try:
            row = await pool.fetchrow(
                """
                INSERT INTO ad_links (slug, title)
                VALUES ($1, $2)
                RETURNING id, slug, title, clicks, created_at, archived_at
                """,
                candidate,
                name,
            )
            return dict(row)
        except asyncpg.exceptions.UniqueViolationError:
            continue
    raise ValueError("Не удалось подобрать код ссылки, задайте другой")


async def archive_ad_link(link_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE ad_links
        SET archived_at = timezone('utc', now())
        WHERE id = $1 AND archived_at IS NULL
        RETURNING id
        """,
        int(link_id),
    )
    return bool(row)


async def list_ad_links(*, include_archived: bool = False) -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT
            l.id,
            l.slug,
            l.title,
            COALESCE(l.clicks, 0)::int AS clicks,
            l.created_at,
            l.archived_at,
            COUNT(u.telegram_id)::int AS users,
            COUNT(u.telegram_id) FILTER (WHERE u.trial_used)::int AS trial,
            COUNT(u.telegram_id) FILTER (WHERE COALESCE(u.has_paid_topup, FALSE))::int AS paid
        FROM ad_links l
        LEFT JOIN users u ON u.ad_link_id = l.id
        WHERE ($1::bool OR l.archived_at IS NULL)
        GROUP BY l.id
        ORDER BY l.created_at DESC, l.id DESC
        """,
        bool(include_archived),
    )
    return [dict(r) for r in rows]


async def claim_referral_reward(telegram_id: int, *, require_paid: bool = True) -> int | None:
    paid_sql = "AND COALESCE(has_paid_topup, FALSE)" if require_paid else ""
    row = await _pool_req().fetchrow(
        f"""
        UPDATE users
        SET referral_rewarded = TRUE
        WHERE telegram_id = $1
          AND referred_by IS NOT NULL
          AND referral_rewarded = FALSE
          {paid_sql}
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


def _mod_msg_key(kind: str, item_id: int) -> str:
    prefix = "story_mod" if kind == "story" else f"{kind}_mod"
    return f"{prefix}:{int(item_id)}"


async def set_mod_messages(kind: str, item_id: int, items: list[dict]) -> None:
    payload = json.dumps(items, ensure_ascii=False) if items else ""
    await set_kv(_mod_msg_key(kind, item_id), payload)


async def pop_mod_messages(kind: str, item_id: int) -> list[dict]:
    key = _mod_msg_key(kind, item_id)
    pool = _pool_req()
    async with pool.acquire() as conn:
        async with conn.transaction():
            raw = await conn.fetchval(
                "SELECT value FROM app_flags WHERE key = $1 FOR UPDATE",
                key,
            )
            await conn.execute(
                """
                INSERT INTO app_flags (key, value) VALUES ($1, '')
                ON CONFLICT (key) DO UPDATE SET value = ''
                """,
                key,
            )
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            out.append(
                {
                    "chat_id": int(item["chat_id"]),
                    "message_id": int(item["message_id"]),
                    "html": str(item.get("html") or ""),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


async def set_story_mod_messages(telegram_id: int, items: list[dict]) -> None:
    await set_mod_messages("story", telegram_id, items)


async def pop_story_mod_messages(telegram_id: int) -> list[dict]:
    return await pop_mod_messages("story", telegram_id)


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


async def claim_welcome_intro(telegram_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET welcome_intro_sent_at = timezone('utc', now())
        WHERE telegram_id = $1
          AND welcome_intro_sent_at IS NULL
        RETURNING telegram_id
        """,
        int(telegram_id),
    )
    return bool(row)


async def set_welcome_sticker_file_id(file_id: str) -> None:
    await set_kv("welcome_sticker_file_id", str(file_id or "").strip())


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


async def claim_trial_balance(telegram_id: int, amount: int, *, signup_only: bool = False) -> int | None:
    if amount < 1:
        return None
    extra = ""
    if signup_only:
        extra = """
          AND COALESCE(has_paid_topup, FALSE) = FALSE
          AND remnawave_id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM devices d WHERE d.telegram_id = users.telegram_id
          )
        """
    row = await _pool_req().fetchrow(
        f"""
        UPDATE users SET
            trial_used = TRUE,
            balance_rub = COALESCE(balance_rub, 0) + $2,
            low_balance_notified_at = NULL
        WHERE telegram_id = $1
          AND trial_used = FALSE
          {extra}
        RETURNING balance_rub
        """,
        telegram_id,
        amount,
    )
    if not row:
        return None
    return int(row["balance_rub"])


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
    used = panel_used_traffic_bytes(panel)
    life = panel_lifetime_traffic_bytes(panel)
    await _pool_req().execute(
        """
        UPDATE users SET
            remnawave_id = COALESCE($2, remnawave_id),
            remnawave_uuid = COALESCE($3, remnawave_uuid),
            expire_at = $4,
            panel_status = $5,
            subscription_url = $6,
            last_synced_at = $7,
            used_traffic_bytes = COALESCE($8, used_traffic_bytes),
            lifetime_traffic_bytes = GREATEST(COALESCE($9, 0), COALESCE(lifetime_traffic_bytes, 0))
        WHERE telegram_id = $1
        """,
        telegram_id,
        remnawave_id,
        uuid,
        expire_at,
        str(panel.get("status") or "") or None,
        panel.get("subscriptionUrl") or None,
        _utc_now(),
        used,
        life,
    )
    if remnawave_id is not None:
        await _pool_req().execute(
            """
            UPDATE devices SET
                used_traffic_bytes = COALESCE($2, used_traffic_bytes),
                lifetime_traffic_bytes = GREATEST(COALESCE($3, 0), COALESCE(lifetime_traffic_bytes, 0))
            WHERE remnawave_id = $1
            """,
            remnawave_id,
            used,
            life,
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
    online = panel_online_at(panel)
    used = panel_used_traffic_bytes(panel)
    life = panel_lifetime_traffic_bytes(panel)
    if remnawave_id is None and not uuid:
        return None
    return remnawave_id, uuid, expire_at, status, sub, online, used, life


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
    used = [r[6] for r in rows]
    life = [r[7] for r in rows]
    now = _utc_now()
    pool = _pool_req()
    await pool.execute(
        """
        UPDATE devices d SET
            remnawave_uuid = COALESCE(v.uuid, d.remnawave_uuid),
            subscription_url = COALESCE(v.sub, d.subscription_url),
            expire_at = COALESCE(v.expire_at, d.expire_at),
            panel_status = COALESCE(v.status, d.panel_status),
            last_online_at = CASE
                WHEN v.online_at IS NULL THEN d.last_online_at
                WHEN d.last_online_at IS NULL OR v.online_at > d.last_online_at THEN v.online_at
                ELSE d.last_online_at
            END,
            used_traffic_bytes = COALESCE(v.used_bytes, d.used_traffic_bytes),
            lifetime_traffic_bytes = GREATEST(COALESCE(v.life_bytes, 0), COALESCE(d.lifetime_traffic_bytes, 0))
        FROM unnest(
            $1::bigint[], $2::text[], $3::timestamptz[], $4::text[], $5::text[],
            $6::timestamptz[], $7::bigint[], $8::bigint[]
        ) AS v(pid, uuid, expire_at, status, sub, online_at, used_bytes, life_bytes)
        WHERE d.remnawave_id IS NOT NULL AND d.remnawave_id = v.pid
        """,
        ids,
        uuids,
        expires,
        statuses,
        subs,
        onlines,
        used,
        life,
    )
    result = await pool.execute(
        """
        UPDATE users u SET
            remnawave_uuid = COALESCE(v.uuid, u.remnawave_uuid),
            expire_at = v.expire_at,
            panel_status = v.status,
            subscription_url = COALESCE(v.sub, u.subscription_url),
            last_synced_at = $8,
            used_traffic_bytes = COALESCE(v.used_bytes, u.used_traffic_bytes),
            lifetime_traffic_bytes = GREATEST(COALESCE(v.life_bytes, 0), COALESCE(u.lifetime_traffic_bytes, 0))
        FROM unnest(
            $1::bigint[], $2::text[], $3::timestamptz[], $4::text[], $5::text[],
            $6::bigint[], $7::bigint[]
        ) AS v(pid, uuid, expire_at, status, sub, used_bytes, life_bytes)
        WHERE u.remnawave_id IS NOT NULL AND u.remnawave_id = v.pid
        """,
        ids,
        uuids,
        expires,
        statuses,
        subs,
        used,
        life,
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
            last_synced_at = $8,
            used_traffic_bytes = COALESCE(v.used_bytes, u.used_traffic_bytes),
            lifetime_traffic_bytes = GREATEST(COALESCE(v.life_bytes, 0), COALESCE(u.lifetime_traffic_bytes, 0))
        FROM unnest(
            $1::bigint[], $2::text[], $3::timestamptz[], $4::text[], $5::text[],
            $6::bigint[], $7::bigint[]
        ) AS v(pid, uuid, expire_at, status, sub, used_bytes, life_bytes)
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
        used,
        life,
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
    expire_raw = panel.get("expireAt")
    expire_at = None
    if expire_raw:
        try:
            expire_at = datetime.fromisoformat(str(expire_raw).replace("Z", "+00:00"))
        except ValueError:
            expire_at = None
    row = await _pool_req().fetchrow(
        """
        UPDATE devices SET
            remnawave_uuid = COALESCE($2, remnawave_uuid),
            subscription_url = $3,
            expire_at = COALESCE($4, expire_at),
            panel_status = COALESCE($5, panel_status),
            used_traffic_bytes = COALESCE($6, used_traffic_bytes),
            lifetime_traffic_bytes = GREATEST(COALESCE($7, 0), COALESCE(lifetime_traffic_bytes, 0))
        WHERE remnawave_id = $1
        RETURNING title
        """,
        remnawave_id,
        uuid,
        panel.get("subscriptionUrl") or None,
        expire_at,
        str(panel.get("status") or "") or None,
        panel_used_traffic_bytes(panel),
        panel_lifetime_traffic_bytes(panel),
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


async def credit_referral_rub(telegram_id: int, amount: int) -> int:
    if amount < 1:
        local = await get_user(telegram_id)
        return int((local or {}).get("balance_rub") or 0)
    row = await _pool_req().fetchrow(
        """
        UPDATE users SET
            balance_rub = COALESCE(balance_rub, 0) + $2,
            referral_earned = COALESCE(referral_earned, 0) + $2,
            low_balance_notified_at = NULL
        WHERE telegram_id = $1
        RETURNING balance_rub
        """,
        telegram_id,
        amount,
    )
    return int(row["balance_rub"]) if row else 0


async def ensure_referral_earned(telegram_id: int, amount: int) -> int:
    need = max(0, int(amount or 0))
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET referral_earned = $2
        WHERE telegram_id = $1
          AND COALESCE(referral_earned, 0) < $2
        RETURNING referral_earned
        """,
        int(telegram_id),
        need,
    )
    if row:
        return int(row["referral_earned"] or 0)
    local = await get_user(telegram_id)
    return int((local or {}).get("referral_earned") or 0)


async def referral_credit_sum(telegram_id: int) -> int:
    val = await _pool_req().fetchval(
        """
        SELECT COALESCE(SUM(amount), 0)::int
        FROM billing_events
        WHERE telegram_id = $1
          AND kind = 'referral'
          AND amount > 0
        """,
        int(telegram_id),
    )
    return int(val or 0)


async def referral_wallet(telegram_id: int) -> dict:
    row = await _pool_req().fetchrow(
        """
        SELECT
            COALESCE(u.balance_rub, 0)::int AS balance_rub,
            COALESCE(u.referral_earned, 0)::int AS referral_earned,
            COALESCE(u.referral_withdrawn, 0)::int AS referral_withdrawn,
            COALESCE((
                SELECT SUM(p.amount)::int
                FROM referral_payouts p
                WHERE p.telegram_id = u.telegram_id AND p.status = 'pending'
            ), 0) AS pending
        FROM users u
        WHERE u.telegram_id = $1
        """,
        telegram_id,
    )
    if not row:
        return {
            "balance_rub": 0,
            "earned": 0,
            "withdrawn": 0,
            "pending": 0,
            "available": 0,
        }
    earned = int(row["referral_earned"] or 0)
    withdrawn = int(row["referral_withdrawn"] or 0)
    pending = int(row["pending"] or 0)
    leftover = max(0, earned - withdrawn - pending)
    balance = int(row["balance_rub"] or 0)
    return {
        "balance_rub": balance,
        "earned": earned,
        "withdrawn": withdrawn,
        "pending": pending,
        "available": min(max(0, balance), leftover),
    }


async def list_referred_friends(telegram_id: int, limit: int = 80) -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT
            first_name,
            username,
            COALESCE(has_paid_topup, FALSE) AS paid,
            created_at
        FROM users
        WHERE referred_by = $1
        ORDER BY COALESCE(has_paid_topup, FALSE) ASC, created_at DESC
        LIMIT $2
        """,
        int(telegram_id),
        max(1, min(int(limit), 80)),
    )
    friends: list[dict] = []
    for row in rows:
        name = str(row["first_name"] or "").strip() or "друг"
        handle = str(row["username"] or "").strip().lstrip("@")
        paid = bool(row["paid"])
        friends.append(
            {
                "name": name[:64],
                "username": handle[:32] if handle else None,
                "paid": paid,
                "status": "есть оплата" if paid else "ещё без оплаты",
            }
        )
    return friends


async def referral_stats(telegram_id: int) -> dict:
    row = await _pool_req().fetchrow(
        """
        SELECT
            COUNT(*)::int AS invited,
            COUNT(*) FILTER (WHERE referral_rewarded)::int AS rewarded
        FROM users
        WHERE referred_by = $1
        """,
        int(telegram_id),
    )
    if not row:
        return {"invited": 0, "rewarded": 0}
    return {
        "invited": int(row["invited"] or 0),
        "rewarded": int(row["rewarded"] or 0),
    }


async def create_referral_payout(telegram_id: int, amount: int, details: str) -> dict | None:
    if amount < 1:
        return None
    note = (details or "").strip()
    pool = _pool_req()
    async with pool.acquire() as conn:
        async with conn.transaction():
            user = await conn.fetchrow(
                """
                SELECT
                    COALESCE(balance_rub, 0)::int AS balance_rub,
                    COALESCE(referral_earned, 0)::int AS referral_earned,
                    COALESCE(referral_withdrawn, 0)::int AS referral_withdrawn
                FROM users
                WHERE telegram_id = $1
                FOR UPDATE
                """,
                telegram_id,
            )
            if not user:
                return None
            exists = await conn.fetchval(
                """
                SELECT 1 FROM referral_payouts
                WHERE telegram_id = $1 AND status = 'pending'
                """,
                telegram_id,
            )
            if exists:
                return None
            leftover = max(
                0,
                int(user["referral_earned"]) - int(user["referral_withdrawn"]),
            )
            available = min(int(user["balance_rub"]), leftover)
            if available < amount:
                return None
            spent = await conn.fetchrow(
                """
                UPDATE users SET balance_rub = balance_rub - $2
                WHERE telegram_id = $1 AND COALESCE(balance_rub, 0) >= $2
                RETURNING balance_rub
                """,
                telegram_id,
                amount,
            )
            if not spent:
                return None
            row = await conn.fetchrow(
                """
                INSERT INTO referral_payouts (telegram_id, amount, details, status)
                VALUES ($1, $2, $3, 'pending')
                RETURNING *
                """,
                telegram_id,
                amount,
                note,
            )
    return _jsonable(dict(row)) if row else None


async def get_referral_payout(payout_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        "SELECT * FROM referral_payouts WHERE id = $1",
        payout_id,
    )
    return _jsonable(dict(row)) if row else None


async def resolve_referral_payout(
    payout_id: int, action: str, admin_id: int | None = None
) -> str:
    if action not in {"paid", "rejected"}:
        return "Неизвестное действие"
    pool = _pool_req()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT * FROM referral_payouts WHERE id = $1 FOR UPDATE",
                payout_id,
            )
            if not row:
                return "Заявка не найдена"
            if row["status"] != "pending":
                return "Заявка уже обработана"
            telegram_id = int(row["telegram_id"])
            amount = int(row["amount"])
            if action == "rejected":
                await conn.execute(
                    """
                    UPDATE users SET
                        balance_rub = COALESCE(balance_rub, 0) + $2,
                        low_balance_notified_at = NULL
                    WHERE telegram_id = $1
                    """,
                    telegram_id,
                    amount,
                )
            else:
                await conn.execute(
                    """
                    UPDATE users SET
                        referral_withdrawn = COALESCE(referral_withdrawn, 0) + $2
                    WHERE telegram_id = $1
                    """,
                    telegram_id,
                    amount,
                )
            await conn.execute(
                """
                UPDATE referral_payouts
                SET status = $2, resolved_at = timezone('utc', now()), resolved_by = $3
                WHERE id = $1
                """,
                payout_id,
                action,
                admin_id,
            )
    return "ok"


async def admin_list_payouts(
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
            f"""(p.telegram_id::text LIKE ${n}
               OR COALESCE(u.username, '') ILIKE ${n}
               OR COALESCE(u.first_name, '') ILIKE ${n}
               OR COALESCE(p.details, '') ILIKE ${n})"""
        )
    status = str(extra.get("status") or "").strip()
    if status:
        args.append(status)
        clauses.append(f"p.status = ${len(args)}")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = await pool.fetchval(
        f"""
        SELECT COUNT(*)::int
        FROM referral_payouts p
        JOIN users u ON u.telegram_id = p.telegram_id
        {where}
        """,
        *args,
    )
    n = len(args)
    rows = await pool.fetch(
        f"""
        SELECT
            p.*,
            u.username,
            u.first_name,
            COALESCE(u.referral_earned, 0)::int AS referral_earned,
            COALESCE(u.referral_withdrawn, 0)::int AS referral_withdrawn,
            COALESCE(u.balance_rub, 0)::int AS balance_rub
        FROM referral_payouts p
        JOIN users u ON u.telegram_id = p.telegram_id
        {where}
        ORDER BY
            CASE WHEN p.status = 'pending' THEN 0 ELSE 1 END,
            p.created_at DESC
        LIMIT ${n + 1} OFFSET ${n + 2}
        """,
        *args,
        limit,
        offset,
    )
    return [_jsonable(dict(r)) for r in rows], int(total or 0)


async def add_balance_rub(telegram_id: int, amount: int) -> int:
    if amount == 0:
        local = await get_user(telegram_id)
        return int((local or {}).get("balance_rub") or 0)
    row = await _pool_req().fetchrow(
        """
        UPDATE users SET
            balance_rub = COALESCE(balance_rub, 0) + $2,
            low_balance_notified_at = CASE
                WHEN $2 > 0 THEN NULL
                ELSE low_balance_notified_at
            END
        WHERE telegram_id = $1
        RETURNING balance_rub
        """,
        telegram_id,
        amount,
    )
    return int(row["balance_rub"]) if row else 0


async def claim_low_balance_notice(telegram_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET low_balance_notified_at = timezone('utc', now())
        WHERE telegram_id = $1
          AND (
            low_balance_notified_at IS NULL
            OR low_balance_notified_at <= timezone('utc', now()) - INTERVAL '24 hours'
          )
        RETURNING telegram_id
        """,
        telegram_id,
    )
    return row is not None


async def mark_paid_topup(telegram_id: int) -> None:
    await _pool_req().execute(
        "UPDATE users SET has_paid_topup = TRUE WHERE telegram_id = $1",
        telegram_id,
    )


async def flag_on(key: str, *, default: bool = False) -> bool:
    val = await _pool_req().fetchval("SELECT value FROM app_flags WHERE key = $1", key)
    if val is None or str(val).strip() == "":
        return default
    return str(val).lower() in {"1", "true", "on", "yes"}


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
        "invite_nudge": _on("invite_nudge"),
        "info_nudge": _on("info_nudge"),
        "story_nudge": _on("story_nudge"),
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


async def mark_bot_blocked(telegram_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET bot_blocked_at = COALESCE(bot_blocked_at, $2)
        WHERE telegram_id = $1
        RETURNING telegram_id
        """,
        int(telegram_id),
        _utc_now(),
    )
    if not row:
        return False
    await clawback_idle_referral(int(telegram_id))
    return True


async def clawback_idle_referral(invitee_id: int) -> dict | None:
    settings = get_settings()
    if not settings.balance_enabled:
        return None
    amount = int(settings.referral_reward_rub or 0)
    if amount < 1:
        return None
    pool = _pool_req()
    async with pool.acquire() as conn:
        async with conn.transaction():
            invitee = await conn.fetchrow(
                """
                SELECT telegram_id, referred_by, trial_used, has_paid_topup,
                       referral_rewarded, referral_clawback_at, first_name
                FROM users
                WHERE telegram_id = $1
                FOR UPDATE
                """,
                int(invitee_id),
            )
            if not invitee:
                return None
            if invitee["trial_used"] or invitee["has_paid_topup"]:
                return None
            if not invitee["referral_rewarded"] or invitee["referral_clawback_at"]:
                return None
            referrer_id = invitee["referred_by"]
            if not referrer_id:
                return None
            referrer_id = int(referrer_id)
            await conn.execute(
                """
                UPDATE users
                SET referral_rewarded = FALSE,
                    referral_clawback_at = timezone('utc', now())
                WHERE telegram_id = $1
                """,
                int(invitee_id),
            )
            after = await conn.fetchrow(
                """
                UPDATE users
                SET balance_rub = COALESCE(balance_rub, 0) - $2,
                    referral_earned = GREATEST(0, COALESCE(referral_earned, 0) - $2)
                WHERE telegram_id = $1
                RETURNING balance_rub
                """,
                referrer_id,
                amount,
            )
            if not after:
                return None
            balance_after = int(after["balance_rub"] or 0)
            invitee_name = invitee["first_name"]
    await log_billing_event(
        referrer_id,
        "referral_revoke",
        source="auto",
        amount=-amount,
        balance_after=balance_after,
        note=f"Возврат за друга {invitee_id}: заблокировал бота без триала",
    )
    return {
        "referrer_id": referrer_id,
        "invitee_id": int(invitee_id),
        "amount": amount,
        "balance_after": balance_after,
        "invitee_name": invitee_name,
    }


async def list_idle_bot_blockers(limit: int) -> tuple[list[int], int]:
    cap = max(1, min(500, int(limit)))
    pool = _pool_req()
    total = await pool.fetchval(
        """
        SELECT COUNT(*)::int FROM users
        WHERE bot_blocked_at IS NOT NULL
          AND NOT trial_used
          AND NOT COALESCE(has_paid_topup, FALSE)
        """
    )
    rows = await pool.fetch(
        """
        SELECT telegram_id
        FROM users
        WHERE bot_blocked_at IS NOT NULL
          AND NOT trial_used
          AND NOT COALESCE(has_paid_topup, FALSE)
        ORDER BY bot_blocked_at ASC, telegram_id
        LIMIT $1
        """,
        cap,
    )
    return [int(r["telegram_id"]) for r in rows], int(total or 0)


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
        "UPDATE devices SET last_billed_on = NULL, last_billed_at = NULL WHERE telegram_id = $1",
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
            await conn.execute("DELETE FROM referral_payouts WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM message_log WHERE telegram_id = $1", telegram_id)
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


async def take_device_charges(telegram_id: int, price: int, count: int) -> int:
    n = max(0, int(count))
    unit = max(0, int(price))
    if n < 1:
        return 0
    if unit < 1:
        return n
    pool = _pool_req()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT COALESCE(balance_rub, 0) AS bal
                FROM users
                WHERE telegram_id = $1
                FOR UPDATE
                """,
                telegram_id,
            )
            if not row:
                return 0
            paid = min(n, int(row["bal"]) // unit)
            if paid < 1:
                return 0
            await conn.execute(
                "UPDATE users SET balance_rub = COALESCE(balance_rub, 0) - $2 WHERE telegram_id = $1",
                telegram_id,
                paid * unit,
            )
            return paid


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
        INSERT INTO devices (telegram_id, title, remnawave_id, last_billed_on, last_billed_at, platform, client)
        VALUES ($1, $2, $3, (timezone('utc', now()))::date, timezone('utc', now()), $4, $5)
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
        SELECT id, telegram_id, title, remnawave_id, remnawave_uuid
        FROM devices
        WHERE remnawave_id IS NOT NULL
          AND UPPER(COALESCE(panel_status, '')) <> 'DISABLED'
          AND (last_billed_at IS NULL OR last_billed_at <= timezone('utc', now()) - INTERVAL '24 hours')
          AND (last_billed_at IS NOT NULL OR last_billed_on IS NULL OR last_billed_on < (timezone('utc', now()))::date)
          AND telegram_id NOT IN (SELECT telegram_id FROM users WHERE blocked_at IS NOT NULL)
        ORDER BY id
        """
    )
    return [dict(r) for r in rows]


async def devices_needing_revive(*, refresh_hours: int = 36) -> list[dict]:
    hours = max(6, int(refresh_hours))
    rows = await _pool_req().fetch(
        """
        SELECT d.id, d.telegram_id, d.title, d.remnawave_id, d.remnawave_uuid
        FROM devices d
        JOIN users u ON u.telegram_id = d.telegram_id
        WHERE d.remnawave_id IS NOT NULL
          AND u.blocked_at IS NULL
          AND d.last_billed_at IS NOT NULL
          AND d.last_billed_at > timezone('utc', now()) - INTERVAL '24 hours'
          AND (
            d.expire_at IS NULL
            OR d.expire_at <= timezone('utc', now()) + ($1::int * INTERVAL '1 hour')
            OR UPPER(COALESCE(d.panel_status, '')) <> 'ACTIVE'
          )
        ORDER BY d.id
        """,
        hours,
    )
    return [dict(r) for r in rows]


async def devices_to_retry_disable() -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT d.id, d.telegram_id, d.title, d.remnawave_id, d.remnawave_uuid
        FROM devices d
        WHERE d.remnawave_id IS NOT NULL
          AND UPPER(COALESCE(d.panel_status, '')) <> 'DISABLED'
          AND (d.last_billed_at IS NULL OR d.last_billed_at <= timezone('utc', now()) - INTERVAL '24 hours')
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
              AND e.kind IN ('disable', 'charge', 'pause', 'revive')
              AND e.created_at >= (timezone('utc', now()))::date
          )
        ORDER BY d.id
        """
    )
    return [dict(r) for r in rows]


async def mark_device_billed(device_id: int) -> None:
    await mark_devices_billed([device_id])


async def mark_devices_billed(
    device_ids: list[int],
    *,
    status: str | None = None,
    expire_at: datetime | None = None,
    touch_billed: bool = True,
) -> None:
    ids = [int(x) for x in device_ids if x is not None]
    if not ids:
        return
    if touch_billed:
        await _pool_req().execute(
            """
            UPDATE devices
            SET last_billed_on = (timezone('utc', now()))::date,
                last_billed_at = timezone('utc', now()),
                panel_status = COALESCE($2, panel_status),
                expire_at = COALESCE($3, expire_at)
            WHERE id = ANY($1::bigint[])
            """,
            ids,
            status,
            expire_at,
        )
        return
    await _pool_req().execute(
        """
        UPDATE devices
        SET panel_status = COALESCE($2, panel_status),
            expire_at = COALESCE($3, expire_at)
        WHERE id = ANY($1::bigint[])
        """,
        ids,
        status,
        expire_at,
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
        if key == "devices":
            items = value
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except ValueError:
                    items = []
            if not isinstance(items, list):
                items = []
            cleaned = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                cleaned.append(
                    {
                        k: v.isoformat() if hasattr(v, "isoformat") else v
                        for k, v in item.items()
                    }
                )
            out[key] = cleaned
            continue
        if hasattr(value, "isoformat"):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def _msg_error(extra) -> str:
    data = extra
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("error") or data.get("error_raw") or "").strip()


def _msg_row(row: dict) -> dict:
    item = _jsonable(row)
    extra = item.get("extra")
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
            item["extra"] = extra
        except ValueError:
            extra = {}
    item["error"] = _msg_error(extra)
    return item


async def log_bot_message(
    *,
    kind: str,
    source: str = "auto",
    telegram_id: int | None = None,
    username: str | None = None,
    first_name: str | None = None,
    title: str = "",
    body: str = "",
    status: str = "sent",
    extra: dict | None = None,
) -> None:
    try:
        await _pool_req().execute(
            """
            INSERT INTO message_log (
                kind, source, telegram_id, username, first_name, title, body, status, extra
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
            """,
            str(kind or "")[:40],
            "manual" if source == "manual" else "auto",
            int(telegram_id) if telegram_id else None,
            (username or "")[:64] or None,
            (first_name or "")[:128] or None,
            str(title or "")[:160],
            str(body or "")[:3500],
            str(status or "sent")[:20],
            json.dumps(extra or {}, ensure_ascii=False, default=str),
        )
    except Exception:
        logging.getLogger("rm-shop.db").debug("Не удалось записать журнал сообщений", exc_info=True)
        return
    if str(status or "") == "failed" and telegram_id and is_user_blocked_bot(extra=extra or {}):
        try:
            await mark_bot_blocked(int(telegram_id))
        except Exception:
            logging.getLogger("rm-shop.db").debug("Не удалось отметить блок бота %s", telegram_id, exc_info=True)


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
            COUNT(*) FILTER (WHERE blocked_at IS NOT NULL)::int AS blocked,
            COUNT(*) FILTER (WHERE bot_blocked_at IS NOT NULL)::int AS bot_blocked,
            COUNT(*) FILTER (
                WHERE bot_blocked_at IS NOT NULL
                  AND NOT trial_used
                  AND NOT COALESCE(has_paid_topup, FALSE)
            )::int AS bot_blocked_idle,
            COALESCE((SELECT COUNT(*)::int FROM referral_payouts WHERE status = 'pending'), 0) AS payouts_pending
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
    online = await pool.fetchrow(
        """
        WITH seen AS (
            SELECT telegram_id, MAX(last_online_at) AS last_seen
            FROM devices
            WHERE last_online_at IS NOT NULL
            GROUP BY telegram_id
        )
        SELECT
            COUNT(*) FILTER (WHERE last_seen >= NOW() - INTERVAL '1 day')::int AS day,
            COUNT(*) FILTER (
                WHERE last_seen >= NOW() - INTERVAL '2 days'
                  AND last_seen < NOW() - INTERVAL '1 day'
            )::int AS day_prev,
            COUNT(*) FILTER (WHERE last_seen >= NOW() - INTERVAL '7 days')::int AS week,
            COUNT(*) FILTER (
                WHERE last_seen >= NOW() - INTERVAL '14 days'
                  AND last_seen < NOW() - INTERVAL '7 days'
            )::int AS week_prev,
            COUNT(*) FILTER (WHERE last_seen >= NOW() - INTERVAL '30 days')::int AS month,
            COUNT(*) FILTER (
                WHERE last_seen >= NOW() - INTERVAL '60 days'
                  AND last_seen < NOW() - INTERVAL '30 days'
            )::int AS month_prev
        FROM seen
        """
    )
    broadcast_users = await pool.fetchval(
        "SELECT COUNT(*)::int FROM users WHERE blocked_at IS NULL"
    )
    broadcast_using = await pool.fetchval(
        """
        SELECT COUNT(*)::int FROM users u
        WHERE u.blocked_at IS NULL
          AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)
        """
    )
    broadcast_unused = await pool.fetchval(
        """
        SELECT COUNT(*)::int FROM users u
        WHERE u.blocked_at IS NULL
          AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)
        """
    )
    return {
        "users": dict(users) if users else {},
        "orders": {r["status"]: r["n"] for r in orders},
        "plans": {r["plan_code"]: r["n"] for r in plans},
        "promo_uses": int(promo or 0),
        "stars_payments": int(stars or 0),
        "vpn_reports": int(await pool.fetchval("SELECT COUNT(*)::int FROM vpn_reports") or 0),
        "tickets_open": int(
            await pool.fetchval("SELECT COUNT(*)::int FROM tickets WHERE status = 'open'") or 0
        ),
        "billing_today": dict(billing_today) if billing_today else {},
        "online": dict(online) if online else {},
        "broadcast_users": int(broadcast_users or 0),
        "broadcast_using": int(broadcast_using or 0),
        "broadcast_unused": int(broadcast_unused or 0),
        "funnel": await admin_funnel(),
    }


_FUNNEL_SQL = """
WITH cohort AS (
    SELECT
        u.telegram_id,
        u.trial_used,
        u.accepted_legal_at,
        u.referred_by,
        u.ad_link_id,
        u.blocked_at,
        COALESCE(u.has_paid_topup, FALSE) AS has_paid
    FROM users u
    WHERE ($1::timestamptz IS NULL OR u.created_at >= $1)
      AND ($2::timestamptz IS NULL OR u.created_at < $2)
),
flags AS (
    SELECT
        c.telegram_id,
        c.referred_by IS NOT NULL AS from_ref,
        c.ad_link_id IS NOT NULL AS from_ad,
        c.referred_by IS NULL AND c.ad_link_id IS NULL AS organic,
        c.accepted_legal_at IS NOT NULL AS legal,
        COALESCE(c.trial_used, FALSE) AS trial,
        c.blocked_at IS NOT NULL AS blocked,
        EXISTS (
            SELECT 1 FROM devices d WHERE d.telegram_id = c.telegram_id
        ) AS has_device,
        EXISTS (
            SELECT 1 FROM devices d
            WHERE d.telegram_id = c.telegram_id AND d.last_online_at IS NOT NULL
        ) AS connected,
        EXISTS (
            SELECT 1 FROM rollypay_orders o WHERE o.telegram_id = c.telegram_id
        ) AS checkout,
        (
            c.has_paid
            OR EXISTS (
                SELECT 1 FROM rollypay_orders o
                WHERE o.telegram_id = c.telegram_id AND o.status = 'granted'
            )
            OR EXISTS (
                SELECT 1 FROM payments p WHERE p.telegram_id = c.telegram_id
            )
        ) AS paid,
        (
            SELECT COUNT(*)::int FROM rollypay_orders o
            WHERE o.telegram_id = c.telegram_id AND o.status = 'granted'
        ) >= 2 AS repeat_paid,
        EXISTS (
            SELECT 1 FROM users inv WHERE inv.referred_by = c.telegram_id
        ) AS invited,
        EXISTS (
            SELECT 1 FROM promo_uses p WHERE p.telegram_id = c.telegram_id
        ) AS promo
    FROM cohort c
),
invitees AS (
    SELECT
        u.telegram_id,
        u.accepted_legal_at IS NOT NULL AS legal,
        COALESCE(u.trial_used, FALSE) AS trial,
        EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id) AS has_device,
        EXISTS (
            SELECT 1 FROM devices d
            WHERE d.telegram_id = u.telegram_id AND d.last_online_at IS NOT NULL
        ) AS connected,
        EXISTS (SELECT 1 FROM rollypay_orders o WHERE o.telegram_id = u.telegram_id) AS checkout,
        (
            COALESCE(u.has_paid_topup, FALSE)
            OR EXISTS (
                SELECT 1 FROM rollypay_orders o
                WHERE o.telegram_id = u.telegram_id AND o.status = 'granted'
            )
            OR EXISTS (
                SELECT 1 FROM payments p WHERE p.telegram_id = u.telegram_id
            )
        ) AS paid
    FROM users u
    WHERE u.referred_by IN (SELECT telegram_id FROM cohort)
)
SELECT
    (SELECT COUNT(*) FROM flags)::int AS entered,
    (SELECT COUNT(*) FROM flags WHERE from_ref)::int AS from_ref,
    (SELECT COUNT(*) FROM flags WHERE from_ad)::int AS from_ad,
    (SELECT COUNT(*) FROM flags WHERE organic)::int AS organic,
    (SELECT COUNT(*) FROM flags WHERE legal)::int AS legal,
    (SELECT COUNT(*) FROM flags WHERE trial)::int AS trial,
    (SELECT COUNT(*) FROM flags WHERE has_device)::int AS device,
    (SELECT COUNT(*) FROM flags WHERE connected)::int AS connected,
    (SELECT COUNT(*) FROM flags WHERE checkout OR paid)::int AS checkout,
    (SELECT COUNT(*) FROM flags WHERE paid)::int AS paid,
    (SELECT COUNT(*) FROM flags WHERE repeat_paid)::int AS repeat_paid,
    (SELECT COUNT(*) FROM flags WHERE invited)::int AS referred,
    (SELECT COUNT(*) FROM flags WHERE promo)::int AS promo,
    (SELECT COUNT(*) FROM flags WHERE blocked)::int AS blocked,
    (SELECT COUNT(*) FROM flags WHERE has_device AND NOT connected)::int AS device_no_online,
    (SELECT COUNT(*) FROM flags WHERE (checkout OR paid) AND NOT paid)::int AS checkout_drop,
    (SELECT COUNT(*) FROM flags WHERE NOT legal)::int AS no_legal,
    (SELECT COUNT(*) FROM invitees)::int AS inv_entered,
    (SELECT COUNT(*) FROM invitees WHERE legal)::int AS inv_legal,
    (SELECT COUNT(*) FROM invitees WHERE trial)::int AS inv_trial,
    (SELECT COUNT(*) FROM invitees WHERE has_device)::int AS inv_device,
    (SELECT COUNT(*) FROM invitees WHERE connected)::int AS inv_connected,
    (SELECT COUNT(*) FROM invitees WHERE checkout OR paid)::int AS inv_checkout,
    (SELECT COUNT(*) FROM invitees WHERE paid)::int AS inv_paid
"""

_FUNNEL_KEYS = (
    "entered",
    "from_ref",
    "from_ad",
    "organic",
    "legal",
    "trial",
    "device",
    "connected",
    "checkout",
    "paid",
    "repeat_paid",
    "referred",
    "promo",
    "blocked",
    "device_no_online",
    "checkout_drop",
    "no_legal",
    "inv_entered",
    "inv_legal",
    "inv_trial",
    "inv_device",
    "inv_connected",
    "inv_checkout",
    "inv_paid",
)


def _funnel_row(row) -> dict:
    if not row:
        return {k: 0 for k in _FUNNEL_KEYS}
    return {k: int(row[k] or 0) for k in _FUNNEL_KEYS}


async def admin_funnel() -> dict:
    pool = _pool_req()
    now = await pool.fetchval("SELECT timezone('utc', now())")

    async def window(start, end):
        row = await pool.fetchrow(_FUNNEL_SQL, start, end)
        return _funnel_row(row)

    d1 = timedelta(days=1)
    d7 = timedelta(days=7)
    d30 = timedelta(days=30)
    d90 = timedelta(days=90)
    return {
        "1d": {
            "label": "сутки",
            "compare": "к предыдущим суткам",
            "current": await window(now - d1, now),
            "previous": await window(now - d1 - d1, now - d1),
        },
        "7d": {
            "label": "7 дней",
            "compare": "к прошлым 7 дням",
            "current": await window(now - d7, now),
            "previous": await window(now - d7 - d7, now - d7),
        },
        "30d": {
            "label": "30 дней",
            "compare": "к прошлым 30 дням",
            "current": await window(now - d30, now),
            "previous": await window(now - d30 - d30, now - d30),
        },
        "90d": {
            "label": "90 дней",
            "compare": "к прошлым 90 дням",
            "current": await window(now - d90, now),
            "previous": await window(now - d90 - d90, now - d90),
        },
        "all": {
            "label": "всё время",
            "compare": "",
            "current": await window(None, None),
            "previous": None,
        },
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
    elif status == "bot_block":
        clauses.append("u.bot_blocked_at IS NOT NULL")
    elif status == "ok":
        clauses.append("u.blocked_at IS NULL AND u.bot_blocked_at IS NULL")
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
    paid = str(extra.get("paid") or "").strip()
    if paid == "yes":
        clauses.append(
            """EXISTS (
                SELECT 1 FROM rollypay_orders o
                WHERE o.telegram_id = u.telegram_id AND o.status = 'granted'
            )"""
        )
    elif paid == "no":
        clauses.append(
            """NOT EXISTS (
                SELECT 1 FROM rollypay_orders o
                WHERE o.telegram_id = u.telegram_id AND o.status = 'granted'
            )"""
        )
    bal_sign = str(extra.get("bal_sign") or "").strip()
    if bal_sign == "pos":
        clauses.append("COALESCE(u.balance_rub, 0) > 0")
    elif bal_sign == "zero":
        clauses.append("COALESCE(u.balance_rub, 0) = 0")
    elif bal_sign == "neg":
        clauses.append("COALESCE(u.balance_rub, 0) < 0")
    for key, op in (("bal_min", ">="), ("bal_max", "<=")):
        raw = str(extra.get(key) or "").strip()
        if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
            args.append(int(raw))
            clauses.append(f"COALESCE(u.balance_rub, 0) {op} ${len(args)}")
    online = str(extra.get("online") or "").strip()
    online_sql = {
        "now": "INTERVAL '15 minutes'",
        "1h": "INTERVAL '1 hour'",
        "1d": "INTERVAL '1 day'",
        "7d": "INTERVAL '7 days'",
        "30d": "INTERVAL '30 days'",
    }.get(online)
    if online == "never":
        clauses.append(
            """
            NOT EXISTS (
                SELECT 1 FROM devices d0
                WHERE d0.telegram_id = u.telegram_id AND d0.last_online_at IS NOT NULL
            )
            """
        )
    elif online_sql:
        clauses.append(
            f"""
            EXISTS (
                SELECT 1 FROM devices d0
                WHERE d0.telegram_id = u.telegram_id
                  AND d0.last_online_at >= NOW() - {online_sql}
            )
            """
        )
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
                   SELECT COALESCE(
                       json_agg(
                           json_build_object(
                               'id', d.id,
                               'title', COALESCE(NULLIF(d.title, ''), 'Устройство'),
                               'platform', COALESCE(d.platform, ''),
                               'client', COALESCE(d.client, ''),
                               'status', COALESCE(d.panel_status, ''),
                               'last_online_at', d.last_online_at,
                               'used_traffic_bytes', GREATEST(
                                   COALESCE(d.used_traffic_bytes, 0),
                                   COALESCE(d.lifetime_traffic_bytes, 0)
                               ),
                               'lifetime_traffic_bytes', GREATEST(
                                   COALESCE(d.lifetime_traffic_bytes, 0),
                                   COALESCE(d.used_traffic_bytes, 0)
                               )
                           )
                           ORDER BY d.id
                       ),
                       '[]'::json
                   )
                   FROM devices d
                   WHERE d.telegram_id = u.telegram_id
               ) AS devices,
               (
                   SELECT MAX(d.last_online_at)
                   FROM devices d
                   WHERE d.telegram_id = u.telegram_id
               ) AS last_online_at,
               GREATEST(
                   COALESCE(
                       (
                           SELECT SUM(
                               GREATEST(
                                   COALESCE(d.used_traffic_bytes, 0),
                                   COALESCE(d.lifetime_traffic_bytes, 0)
                               )
                           )::bigint
                           FROM devices d
                           WHERE d.telegram_id = u.telegram_id
                       ),
                       0
                   ),
                   COALESCE(u.used_traffic_bytes, 0),
                   COALESCE(u.lifetime_traffic_bytes, 0)
               ) AS used_traffic_bytes,
               GREATEST(
                   COALESCE(
                       (
                           SELECT SUM(
                               GREATEST(
                                   COALESCE(d.lifetime_traffic_bytes, 0),
                                   COALESCE(d.used_traffic_bytes, 0)
                               )
                           )::bigint
                           FROM devices d
                           WHERE d.telegram_id = u.telegram_id
                       ),
                       0
                   ),
                   COALESCE(u.lifetime_traffic_bytes, 0),
                   COALESCE(u.used_traffic_bytes, 0)
               ) AS lifetime_traffic_bytes,
               (
                   SELECT COUNT(*)::int FROM users inv WHERE inv.referred_by = u.telegram_id
               ) AS invited_count,
               (
                   SELECT COUNT(*)::int
                   FROM rollypay_orders o
                   WHERE o.telegram_id = u.telegram_id AND o.status = 'granted'
               ) AS paid_topup_count,
               (
                   SELECT MAX(o.created_at)
                   FROM rollypay_orders o
                   WHERE o.telegram_id = u.telegram_id AND o.status = 'granted'
               ) AS last_paid_at,
               (
                   SELECT COALESCE(json_agg(o.plan_code), '[]'::json)
                   FROM rollypay_orders o
                   WHERE o.telegram_id = u.telegram_id AND o.status = 'granted'
               ) AS paid_plan_codes
        FROM users u
        LEFT JOIN users ref ON ref.telegram_id = u.referred_by
        {where}
        ORDER BY u.created_at DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
    """
    total = await pool.fetchval(total_sql, *args)
    rows = await pool.fetch(list_sql, *args, limit, offset)
    settings = get_settings()
    items = []
    for r in rows:
        item = _jsonable(dict(r))
        codes = item.pop("paid_plan_codes", None) or []
        if isinstance(codes, str):
            try:
                codes = json.loads(codes)
            except ValueError:
                codes = []
        if not isinstance(codes, list):
            codes = []
        item["paid_topup_rub"] = sum(settings.topup_rub_for_code(c) for c in codes)
        items.append(item)
    return items, int(total or 0)


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
            f"""(o.order_id ILIKE ${n} OR COALESCE(o.payment_id, '') ILIKE ${n}
               OR o.telegram_id::text LIKE ${n} OR o.status ILIKE ${n}
               OR COALESCE(o.plan_code, '') ILIKE ${n}
               OR COALESCE(u.username, '') ILIKE ${n}
               OR COALESCE(u.first_name, '') ILIKE ${n})"""
        )
    status = str(extra.get("status") or "").strip()
    if status:
        args.append(status)
        clauses.append(f"o.status = ${len(args)}")
    from_d = str(extra.get("from") or "").strip()
    to_d = str(extra.get("to") or "").strip()
    if from_d:
        args.append(from_d)
        clauses.append(f"o.created_at >= ${len(args)}::date")
    if to_d:
        args.append(to_d)
        clauses.append(f"o.created_at < (${len(args)}::date + INTERVAL '1 day')")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = await pool.fetchval(
        f"""
        SELECT COUNT(*)::int FROM rollypay_orders o
        LEFT JOIN users u ON u.telegram_id = o.telegram_id
        {where}
        """,
        *args,
    )
    n = len(args)
    rows = await pool.fetch(
        f"""
        SELECT o.*, u.username, u.first_name
        FROM rollypay_orders o
        LEFT JOIN users u ON u.telegram_id = o.telegram_id
        {where}
        ORDER BY o.created_at DESC
        LIMIT ${n + 1} OFFSET ${n + 2}
        """,
        *args,
        limit,
        offset,
    )
    settings = get_settings()
    items = []
    for r in rows:
        item = _jsonable(dict(r))
        item["amount_rub"] = settings.topup_rub_for_code(item.get("plan_code"))
        items.append(item)
    return items, int(total or 0)


async def admin_topup_summary(limit: int = 50) -> dict:
    pool = _pool_req()
    rows = await pool.fetch(
        """
        SELECT o.telegram_id, u.username, u.first_name, o.plan_code,
               COUNT(*)::int AS n, MAX(o.created_at) AS last_paid_at
        FROM rollypay_orders o
        LEFT JOIN users u ON u.telegram_id = o.telegram_id
        WHERE o.status = 'granted'
        GROUP BY o.telegram_id, u.username, u.first_name, o.plan_code
        """
    )
    settings = get_settings()
    by_user: dict[int, dict] = {}
    for r in rows:
        tid = int(r["telegram_id"])
        rec = by_user.setdefault(
            tid,
            {
                "telegram_id": tid,
                "username": r["username"],
                "first_name": r["first_name"],
                "payments": 0,
                "amount_rub": 0,
                "last_paid_at": None,
            },
        )
        n = int(r["n"] or 0)
        rec["payments"] += n
        rec["amount_rub"] += settings.topup_rub_for_code(r["plan_code"]) * n
        ts = r["last_paid_at"]
        if ts and (rec["last_paid_at"] is None or ts > rec["last_paid_at"]):
            rec["last_paid_at"] = ts
    items = sorted(by_user.values(), key=lambda x: (-int(x["amount_rub"]), x["telegram_id"]))
    cap = max(1, min(200, int(limit)))
    return {
        "payers": len(items),
        "payments": sum(int(x["payments"]) for x in items),
        "amount_rub": sum(int(x["amount_rub"]) for x in items),
        "items": [_jsonable(x) for x in items[:cap]],
    }


async def reset_trial(telegram_id: int) -> bool:
    result = await _pool_req().execute(
        "UPDATE users SET trial_used = FALSE WHERE telegram_id = $1",
        telegram_id,
    )
    return result == "UPDATE 1"


async def list_due_trial_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    rows = await _pool_req().fetch(
        """
        SELECT u.telegram_id, u.first_name, u.trial_used, u.balance_rub
        FROM users u
        WHERE u.trial_nudge_sent_at IS NULL
          AND u.blocked_at IS NULL
          AND COALESCE(u.has_paid_topup, FALSE) = FALSE
          AND u.created_at <= timezone('utc', now()) - INTERVAL '24 hours'
          AND EXISTS (
              SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id
          )
          AND NOT (u.telegram_id = ANY($2::bigint[]))
        ORDER BY u.created_at
        LIMIT $1
        """,
        int(limit),
        skip,
    )
    return [dict(r) for r in rows]


async def list_due_invite_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    rows = await _pool_req().fetch(
        """
        SELECT u.telegram_id, u.first_name
        FROM users u
        WHERE u.invite_nudge_sent_at IS NULL
          AND u.blocked_at IS NULL
          AND u.created_at <= timezone('utc', now()) - INTERVAL '48 hours'
          AND NOT (u.telegram_id = ANY($2::bigint[]))
          AND (
            COALESCE(u.has_paid_topup, FALSE)
            OR EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id)
          )
        ORDER BY u.created_at
        LIMIT $1
        """,
        int(limit),
        skip,
    )
    return [dict(r) for r in rows]


async def list_due_info_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    rows = await _pool_req().fetch(
        """
        SELECT u.telegram_id, u.first_name
        FROM users u
        WHERE u.info_nudge_sent_at IS NULL
          AND u.blocked_at IS NULL
          AND u.created_at <= timezone('utc', now()) - INTERVAL '96 hours'
          AND NOT (u.telegram_id = ANY($2::bigint[]))
        ORDER BY u.created_at
        LIMIT $1
        """,
        int(limit),
        skip,
    )
    return [dict(r) for r in rows]


async def list_due_story_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    rows = await _pool_req().fetch(
        """
        SELECT u.telegram_id, u.first_name
        FROM users u
        WHERE u.story_nudge_sent_at IS NULL
          AND u.blocked_at IS NULL
          AND u.story_rewarded_at IS NULL
          AND u.story_pending_at IS NULL
          AND u.first_online_at IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM devices d
              WHERE d.telegram_id = u.telegram_id
          )
          AND NOT (u.telegram_id = ANY($2::bigint[]))
        ORDER BY u.created_at
        LIMIT $1
        """,
        int(limit),
        skip,
    )
    return [dict(r) for r in rows]


async def mark_nudge_sent(telegram_id: int, kind: str) -> None:
    col = {
        "trial": "trial_nudge_sent_at",
        "invite": "invite_nudge_sent_at",
        "info": "info_nudge_sent_at",
        "story": "story_nudge_sent_at",
    }.get(kind)
    if not col:
        return
    await _pool_req().execute(
        f"""
        UPDATE users
        SET {col} = timezone('utc', now())
        WHERE telegram_id = $1 AND {col} IS NULL
        """,
        int(telegram_id),
    )


async def take_story_nudge(telegram_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET story_nudge_sent_at = timezone('utc', now())
        WHERE telegram_id = $1
          AND story_nudge_sent_at IS NULL
          AND blocked_at IS NULL
          AND story_rewarded_at IS NULL
          AND story_pending_at IS NULL
          AND first_online_at IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM devices d
              WHERE d.telegram_id = users.telegram_id
          )
        RETURNING telegram_id, first_name
        """,
        int(telegram_id),
    )
    return dict(row) if row else None


async def restore_story_nudge(telegram_id: int) -> None:
    await _pool_req().execute(
        """
        UPDATE users
        SET story_nudge_sent_at = NULL
        WHERE telegram_id = $1
          AND story_rewarded_at IS NULL
        """,
        int(telegram_id),
    )


async def mark_first_device_thanks_pending(telegram_id: int) -> None:
    await _pool_req().execute(
        """
        UPDATE users
        SET first_device_thanks_pending = TRUE,
            device_nudge_count = GREATEST(COALESCE(device_nudge_count, 0), 3)
        WHERE telegram_id = $1
          AND first_device_thanks_sent_at IS NULL
        """,
        int(telegram_id),
    )


async def take_first_device_thanks(telegram_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET first_device_thanks_pending = FALSE,
            first_device_thanks_sent_at = timezone('utc', now())
        WHERE telegram_id = $1
          AND first_device_thanks_pending = TRUE
          AND first_device_thanks_sent_at IS NULL
        RETURNING telegram_id
        """,
        int(telegram_id),
    )
    return bool(row)


async def restore_first_device_thanks(telegram_id: int) -> None:
    await _pool_req().execute(
        """
        UPDATE users
        SET first_device_thanks_pending = TRUE,
            first_device_thanks_sent_at = NULL
        WHERE telegram_id = $1
          AND first_device_thanks_sent_at IS NOT NULL
        """,
        int(telegram_id),
    )


async def list_due_device_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    rows = await _pool_req().fetch(
        """
        SELECT u.telegram_id, u.first_name, COALESCE(u.device_nudge_count, 0) AS device_nudge_count
        FROM users u
        WHERE u.blocked_at IS NULL
          AND COALESCE(u.device_nudge_count, 0) < 3
          AND NOT EXISTS (
              SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id
          )
          AND NOT (u.telegram_id = ANY($2::bigint[]))
          AND (
            (
              COALESCE(u.device_nudge_count, 0) = 0
              AND u.created_at <= timezone('utc', now()) - INTERVAL '30 minutes'
              AND u.created_at > timezone('utc', now()) - INTERVAL '36 hours'
            )
            OR (
              COALESCE(u.device_nudge_count, 0) IN (1, 2)
              AND u.device_nudge_at IS NOT NULL
              AND u.device_nudge_at <= timezone('utc', now()) - INTERVAL '24 hours'
            )
          )
        ORDER BY u.created_at
        LIMIT $1
        """,
        int(limit),
        skip,
    )
    return [dict(r) for r in rows]


async def mark_device_nudge_sent(telegram_id: int) -> None:
    await _pool_req().execute(
        """
        UPDATE users
        SET device_nudge_count = LEAST(COALESCE(device_nudge_count, 0) + 1, 3),
            device_nudge_at = timezone('utc', now())
        WHERE telegram_id = $1
        """,
        int(telegram_id),
    )


async def list_due_first_online_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    rows = await _pool_req().fetch(
        """
        SELECT
            u.telegram_id,
            u.first_name,
            COALESCE(u.balance_rub, 0) AS balance_rub,
            (
                SELECT COUNT(*)::int FROM devices d WHERE d.telegram_id = u.telegram_id
            ) AS device_count
        FROM users u
        WHERE u.first_online_nudge_at IS NULL
          AND u.blocked_at IS NULL
          AND u.first_online_at IS NOT NULL
          AND u.first_online_at <= timezone('utc', now()) - INTERVAL '20 hours'
          AND COALESCE(u.has_paid_topup, FALSE) = FALSE
          AND EXISTS (
              SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id
          )
          AND NOT (u.telegram_id = ANY($2::bigint[]))
        ORDER BY u.first_online_at
        LIMIT $1
        """,
        int(limit),
        skip,
    )
    return [dict(r) for r in rows]


async def mark_first_online_nudge_sent(telegram_id: int) -> None:
    await _pool_req().execute(
        """
        UPDATE users
        SET first_online_nudge_at = timezone('utc', now())
        WHERE telegram_id = $1 AND first_online_nudge_at IS NULL
        """,
        int(telegram_id),
    )


async def list_due_trial_end_nudges(
    day_price: int,
    limit: int = 80,
    skip_ids: list[int] | None = None,
) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    price = max(1, int(day_price or 1))
    rows = await _pool_req().fetch(
        """
        SELECT
            u.telegram_id,
            u.first_name,
            COALESCE(u.balance_rub, 0) AS balance_rub,
            (
                SELECT COUNT(*)::int FROM devices d WHERE d.telegram_id = u.telegram_id
            ) AS device_count
        FROM users u
        WHERE u.trial_end_nudge_at IS NULL
          AND u.blocked_at IS NULL
          AND u.first_online_at IS NOT NULL
          AND COALESCE(u.has_paid_topup, FALSE) = FALSE
          AND COALESCE(u.balance_rub, 0) > 0
          AND EXISTS (
              SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id
          )
          AND COALESCE(u.balance_rub, 0) <= $3 * GREATEST(
              (SELECT COUNT(*)::int FROM devices d WHERE d.telegram_id = u.telegram_id),
              1
          )
          AND NOT (u.telegram_id = ANY($2::bigint[]))
        ORDER BY u.first_online_at
        LIMIT $1
        """,
        int(limit),
        skip,
        price,
    )
    return [dict(r) for r in rows]


async def mark_trial_end_nudge_sent(telegram_id: int) -> None:
    await _pool_req().execute(
        """
        UPDATE users
        SET trial_end_nudge_at = timezone('utc', now())
        WHERE telegram_id = $1 AND trial_end_nudge_at IS NULL
        """,
        int(telegram_id),
    )


async def broadcast_audience_counts() -> dict:
    row = await _pool_req().fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE blocked_at IS NULL)::int AS all_n,
            COUNT(*) FILTER (
                WHERE blocked_at IS NULL
                  AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = users.telegram_id)
            )::int AS using_n,
            COUNT(*) FILTER (
                WHERE blocked_at IS NULL
                  AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = users.telegram_id)
            )::int AS unused_n
        FROM users
        """
    )
    return {
        "all": int((row and row["all_n"]) or 0),
        "using": int((row and row["using_n"]) or 0),
        "unused": int((row and row["unused_n"]) or 0),
    }


async def list_broadcast_targets(audience: str = "all") -> list[dict]:
    extra = ""
    kind = str(audience or "all").strip()
    if kind == "using":
        extra = "AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = users.telegram_id)"
    elif kind == "unused":
        extra = "AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = users.telegram_id)"
    rows = await _pool_req().fetch(
        f"""
        SELECT telegram_id, first_name
        FROM users
        WHERE blocked_at IS NULL
        {extra}
        ORDER BY telegram_id
        """
    )
    return [dict(r) for r in rows]


async def list_broadcast_ids(audience: str = "all") -> list[int]:
    return [int(r["telegram_id"]) for r in await list_broadcast_targets(audience)]


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
    pool = _pool_req()
    await pool.execute("DELETE FROM cabinet_tokens WHERE telegram_id = $1", int(telegram_id))
    await pool.execute(
        """
        INSERT INTO cabinet_tokens (token_hash, telegram_id, expires_at)
        VALUES ($1, $2, $3)
        """,
        _cabinet_token_hash(raw),
        int(telegram_id),
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
        WHERE token_hash = $1 AND expires_at > timezone('utc', now())
        """,
        _cabinet_token_hash(token),
    )
    if not row:
        return None
    return int(row["telegram_id"])


async def purge_expired_cabinet_tokens() -> None:
    await _pool_req().execute("DELETE FROM cabinet_tokens WHERE expires_at <= timezone('utc', now())")


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
               SELECT 1 FROM message_log m
               WHERE m.telegram_id = u.telegram_id
                 AND m.kind = 'cabinet_link'
                 AND m.created_at > timezone('utc', now()) - INTERVAL '10 days'
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


async def log_billing_events(events: list[dict]) -> None:
    if not events:
        return
    rows = [
        (
            int(item["telegram_id"]),
            str(item.get("kind") or ""),
            str(item.get("source") or "cron"),
            int(item.get("amount") or 0),
            item.get("balance_after"),
            int(item["device_id"]) if item.get("device_id") is not None else None,
            (str(item.get("device_title") or "").strip() or None),
            (str(item.get("note") or "").strip() or None),
        )
        for item in events
    ]
    try:
        await _pool_req().executemany(
            """
            INSERT INTO billing_events (
                telegram_id, kind, source, amount, balance_after, device_id, device_title, note
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            rows,
        )
    except Exception:
        logging.getLogger("rm-shop.db").exception("Не удалось записать события биллинга")


async def purge_old_billing_events(
    keep_days: int, *, batch: int = 8000, max_batches: int = 40
) -> int:
    days = int(keep_days)
    if days <= 0:
        return 0
    limit = max(500, min(20000, int(batch)))
    rounds = max(1, min(80, int(max_batches)))
    deleted = 0
    pool = _pool_req()
    for _ in range(rounds):
        status = await pool.execute(
            """
            DELETE FROM billing_events
            WHERE id IN (
                SELECT id FROM billing_events
                WHERE created_at < timezone('utc', now()) - ($1::int * INTERVAL '1 day')
                ORDER BY id
                LIMIT $2
            )
            """,
            days,
            limit,
        )
        try:
            n = int(str(status).split()[-1])
        except (TypeError, ValueError, IndexError):
            n = 0
        deleted += n
        if n < limit:
            break
    return deleted


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


_USER_BILLING_KINDS = (
    "charge",
    "pause",
    "disable",
    "revive",
    "trial",
    "admin_balance",
    "admin_grant",
    "trust",
    "trust_collect",
    "device_delete",
    "referral",
    "referral_payout",
    "referral_revoke",
    "story",
)


async def user_billing_history(telegram_id: int, *, days: int = 7) -> list[dict]:
    window = max(1, min(31, int(days)))
    rows = await _pool_req().fetch(
        """
        SELECT id, kind, amount, balance_after, device_title, note, created_at
        FROM billing_events
        WHERE telegram_id = $1
          AND created_at >= timezone('utc', now()) - ($2::int * INTERVAL '1 day')
          AND kind = ANY($3::text[])
        ORDER BY created_at DESC, id DESC
        LIMIT 200
        """,
        int(telegram_id),
        window,
        list(_USER_BILLING_KINDS),
    )
    return [_jsonable(dict(r)) for r in rows]


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


def _message_log_filters(query: str, extra: dict | None = None) -> tuple[list[str], list]:
    extra = extra or {}
    clauses: list[str] = []
    args: list = []
    channel = str(extra.get("channel") or "").strip()
    if channel == "announce":
        clauses.append("kind NOT IN ('maintenance_hit', 'maintenance_out')")
    elif channel == "maint":
        clauses.append("kind IN ('maintenance_hit', 'maintenance_out')")
    source = str(extra.get("source") or "").strip()
    if source in {"auto", "manual"}:
        args.append(source)
        clauses.append(f"source = ${len(args)}")
    kind = str(extra.get("kind") or "").strip()
    if kind:
        args.append(kind)
        clauses.append(f"kind = ${len(args)}")
    status = str(extra.get("status") or "").strip()
    if status:
        args.append(status)
        clauses.append(f"status = ${len(args)}")
    q = (query or "").strip()
    if q:
        args.append(f"%{q}%")
        n = len(args)
        clauses.append(
            f"""(
            COALESCE(username, '') ILIKE ${n}
            OR COALESCE(first_name, '') ILIKE ${n}
            OR COALESCE(title, '') ILIKE ${n}
            OR COALESCE(body, '') ILIKE ${n}
            OR telegram_id::text LIKE ${n}
            )"""
        )
    from_d = str(extra.get("from") or "").strip()
    to_d = str(extra.get("to") or "").strip()
    if from_d:
        args.append(from_d)
        clauses.append(f"created_at >= ${len(args)}::date")
    if to_d:
        args.append(to_d)
        clauses.append(f"created_at < (${len(args)}::date + INTERVAL '1 day')")
    return clauses, args


async def get_message_log(msg_id: int) -> dict | None:
    row = await _pool_req().fetchrow("SELECT * FROM message_log WHERE id = $1", int(msg_id))
    return _msg_row(dict(row)) if row else None


async def admin_list_messages(
    query: str,
    limit: int,
    offset: int,
    extra: dict | None = None,
) -> tuple[list[dict], int]:
    pool = _pool_req()
    clauses, args = _message_log_filters(query, extra)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = await pool.fetchval(f"SELECT COUNT(*)::int FROM message_log {where}", *args)
    n = len(args)
    rows = await pool.fetch(
        f"""
        SELECT * FROM message_log
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT ${n + 1} OFFSET ${n + 2}
        """,
        *args,
        limit,
        offset,
    )
    return [_msg_row(dict(r)) for r in rows], int(total or 0)


async def admin_list_failed_messages(
    query: str,
    limit: int,
    extra: dict | None = None,
) -> tuple[list[dict], int]:
    pool = _pool_req()
    extra = dict(extra or {})
    extra["status"] = "failed"
    clauses, args = _message_log_filters(query, extra)
    clauses.append("telegram_id IS NOT NULL")
    clauses.append("kind <> 'maintenance_hit'")
    where = "WHERE " + " AND ".join(clauses)
    total = await pool.fetchval(f"SELECT COUNT(*)::int FROM message_log {where}", *args)
    n = len(args)
    rows = await pool.fetch(
        f"""
        SELECT * FROM message_log
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT ${n + 1}
        """,
        *args,
        limit,
    )
    return [_msg_row(dict(r)) for r in rows], int(total or 0)


async def open_or_get_ticket(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> tuple[dict, bool]:
    pool = _pool_req()
    row = await pool.fetchrow(
        """
        SELECT * FROM tickets
        WHERE telegram_id = $1 AND status <> 'closed'
        ORDER BY last_message_at DESC, id DESC
        LIMIT 1
        """,
        int(telegram_id),
    )
    if row:
        await pool.execute(
            """
            UPDATE tickets
            SET username = COALESCE($2, username), first_name = COALESCE($3, first_name)
            WHERE id = $1
            """,
            int(row["id"]),
            (username or "")[:64] or None,
            (first_name or "")[:128] or None,
        )
        fresh = await pool.fetchrow("SELECT * FROM tickets WHERE id = $1", int(row["id"]))
        return _jsonable(dict(fresh)), False
    try:
        new = await pool.fetchrow(
            """
            INSERT INTO tickets (telegram_id, username, first_name, status)
            VALUES ($1, $2, $3, 'open')
            RETURNING *
            """,
            int(telegram_id),
            (username or "")[:64] or None,
            (first_name or "")[:128] or None,
        )
    except asyncpg.UniqueViolationError:
        return await open_or_get_ticket(telegram_id, username, first_name)
    return _jsonable(dict(new)), True


_TICKET_LAST_BODY = """
            COALESCE(
                NULLIF(tm.body, ''),
                (
                    SELECT CASE ta.kind
                        WHEN 'photo' THEN 'Фото'
                        WHEN 'video' THEN 'Видео'
                        ELSE COALESCE(NULLIF(ta.original_name, ''), 'Файл')
                    END
                    FROM ticket_attachments ta
                    WHERE ta.message_id = tm.id
                    ORDER BY ta.id
                    LIMIT 1
                ),
                ''
            )
"""


async def add_ticket_message(
    ticket_id: int,
    author: str,
    body: str,
    *,
    user_waiting: bool | None = None,
) -> dict:
    pool = _pool_req()
    who = "admin" if author == "admin" else "user"
    if user_waiting is None:
        status = "open" if who == "user" else "pending"
    else:
        status = "open" if user_waiting else "pending"
    row = await pool.fetchrow(
        """
        INSERT INTO ticket_messages (ticket_id, author, body)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        int(ticket_id),
        who,
        str(body or "")[:2000],
    )
    await pool.execute(
        """
        UPDATE tickets
        SET status = $2,
            last_message_at = timezone('utc', now()),
            closed_at = NULL
        WHERE id = $1
        """,
        int(ticket_id),
        status,
    )
    return _jsonable(dict(row))


async def add_ticket_attachment(message_id: int, meta: dict) -> dict:
    row = await _pool_req().fetchrow(
        """
        INSERT INTO ticket_attachments (
            message_id, stored_name, original_name, mime, kind, size_bytes
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        int(message_id),
        str(meta.get("stored_name") or ""),
        str(meta.get("original_name") or "")[:120],
        str(meta.get("mime") or "application/octet-stream")[:120],
        str(meta.get("kind") or "file")[:16],
        int(meta.get("size_bytes") or 0),
    )
    return _jsonable(dict(row))


async def get_ticket_attachment(att_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        """
        SELECT ta.*, t.id AS ticket_id, t.telegram_id
        FROM ticket_attachments ta
        JOIN ticket_messages tm ON tm.id = ta.message_id
        JOIN tickets t ON t.id = tm.ticket_id
        WHERE ta.id = $1
        """,
        int(att_id),
    )
    return _jsonable(dict(row)) if row else None


async def set_ticket_status(ticket_id: int, status: str) -> None:
    st = str(status or "open")
    if st not in {"open", "pending", "closed"}:
        st = "open"
    closed_sql = "timezone('utc', now())" if st == "closed" else "NULL"
    await _pool_req().execute(
        f"""
        UPDATE tickets
        SET status = $2, closed_at = {closed_sql}
        WHERE id = $1
        """,
        int(ticket_id),
        st,
    )


async def get_ticket(ticket_id: int) -> dict | None:
    row = await _pool_req().fetchrow("SELECT * FROM tickets WHERE id = $1", int(ticket_id))
    return _jsonable(dict(row)) if row else None


async def list_ticket_messages(ticket_id: int) -> list[dict]:
    pool = _pool_req()
    rows = await pool.fetch(
        """
        SELECT * FROM ticket_messages
        WHERE ticket_id = $1
        ORDER BY id ASC
        """,
        int(ticket_id),
    )
    messages = [_jsonable(dict(r)) for r in rows]
    if not messages:
        return messages
    atts = await pool.fetch(
        """
        SELECT * FROM ticket_attachments
        WHERE message_id = ANY($1::bigint[])
        ORDER BY id ASC
        """,
        [int(m["id"]) for m in messages],
    )
    by_msg: dict[int, list[dict]] = {}
    for row in atts:
        item = _jsonable(dict(row))
        by_msg.setdefault(int(row["message_id"]), []).append(item)
    for msg in messages:
        msg["attachments"] = by_msg.get(int(msg["id"]), [])
    return messages


async def user_list_tickets(telegram_id: int, limit: int = 20) -> list[dict]:
    rows = await _pool_req().fetch(
        f"""
        SELECT t.*,
            (
                SELECT {_TICKET_LAST_BODY}
                FROM ticket_messages tm
                WHERE tm.ticket_id = t.id
                ORDER BY tm.id DESC LIMIT 1
            ) AS last_body
        FROM tickets t
        WHERE t.telegram_id = $1
        ORDER BY t.last_message_at DESC, t.id DESC
        LIMIT $2
        """,
        int(telegram_id),
        int(limit),
    )
    return [_jsonable(dict(r)) for r in rows]


async def admin_list_tickets(
    query: str,
    limit: int,
    offset: int,
    extra: dict | None = None,
) -> tuple[list[dict], int]:
    pool = _pool_req()
    extra = extra or {}
    clauses: list[str] = []
    args: list = []
    status = str(extra.get("status") or "").strip()
    if status in {"open", "pending", "closed"}:
        args.append(status)
        clauses.append(f"status = ${len(args)}")
    q = (query or "").strip()
    if q:
        args.append(f"%{q}%")
        n = len(args)
        clauses.append(
            f"""(
            COALESCE(username, '') ILIKE ${n}
            OR COALESCE(first_name, '') ILIKE ${n}
            OR telegram_id::text LIKE ${n}
            OR id::text LIKE ${n}
            )"""
        )
    from_d = str(extra.get("from") or "").strip()
    to_d = str(extra.get("to") or "").strip()
    if from_d:
        args.append(from_d)
        clauses.append(f"last_message_at >= ${len(args)}::date")
    if to_d:
        args.append(to_d)
        clauses.append(f"last_message_at < (${len(args)}::date + INTERVAL '1 day')")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = await pool.fetchval(f"SELECT COUNT(*)::int FROM tickets {where}", *args)
    n = len(args)
    rows = await pool.fetch(
        f"""
        SELECT t.*,
            (
                SELECT {_TICKET_LAST_BODY}
                FROM ticket_messages tm
                WHERE tm.ticket_id = t.id
                ORDER BY tm.id DESC LIMIT 1
            ) AS last_body
        FROM tickets t
        {where}
        ORDER BY
            CASE t.status WHEN 'open' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END,
            t.last_message_at DESC, t.id DESC
        LIMIT ${n + 1} OFFSET ${n + 2}
        """,
        *args,
        limit,
        offset,
    )
    return [_jsonable(dict(r)) for r in rows], int(total or 0)
