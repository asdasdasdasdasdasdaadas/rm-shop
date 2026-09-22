from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
from decimal import Decimal, InvalidOperation
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
        # PostgreSQL must parse statement boundaries: semicolons can also occur
        # inside comments, strings and function bodies. asyncpg supports scripts.
        await conn.execute(schema)
    await _ensure_nudge_defaults()


async def migrate_legacy_promo_codes() -> None:
    if (await get_kv("promo_codes_migrated_v1")) == "1":
        return
    settings = get_settings()
    for code, days in settings.promo_map.items():
        clean = str(code or "").strip().upper()
        try:
            day_n = int(days)
        except (TypeError, ValueError):
            continue
        if not clean or day_n < 1:
            continue
        await _pool_req().execute(
            """
            INSERT INTO promo_codes (code, days, enabled)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (code) DO NOTHING
            """,
            clean,
            day_n,
        )
    await set_kv("promo_codes_migrated_v1", "1")


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
        await set_flag("story_nudge", False)
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
    if (await get_kv("nudge_defaults_v6")) != "1":
        await set_flag("legal_nudge", True)
        await set_kv("nudge_defaults_v6", "1")
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


async def get_user_by_username(username: str) -> dict | None:
    nick = (username or "").strip().lstrip("@").lower()
    if not nick:
        return None
    row = await _pool_req().fetchrow(
        """
        SELECT *
        FROM users
        WHERE username IS NOT NULL
          AND lower(ltrim(username, '@')) = $1
        ORDER BY COALESCE(last_synced_at, created_at) DESC, telegram_id DESC
        LIMIT 1
        """,
        nick,
    )
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


async def create_ad_link(title: str, slug: str = "", *, kind: str = "manual") -> dict:
    name = str(title or "").strip()
    if len(name) < 2:
        raise ValueError("Укажите название ссылки")
    if len(name) > 80:
        raise ValueError("Название слишком длинное")
    link_kind = str(kind or "manual").strip().lower() or "manual"
    if link_kind not in {"manual", "story"}:
        raise ValueError("Неизвестный тип ссылки")
    raw_slug = str(slug or "").strip()
    if raw_slug:
        candidate = raw_slug.lower()
        if candidate.startswith("ad_"):
            candidate = candidate[3:]
        candidate = candidate.replace(" ", "_")
        if not _AD_SLUG_RE.fullmatch(candidate) or not (2 <= len(candidate) <= 32):
            raise ValueError("Код: латиница, цифры и подчёркивание, от 2 до 32 знаков")
        if link_kind == "manual" and candidate.startswith("st_"):
            raise ValueError("Код st_ зарезервирован для сторис")
        base = candidate
    else:
        base = normalize_ad_slug("", title=name)
        if link_kind == "manual" and base.startswith("st_"):
            base = "ad" + secrets.token_hex(3)
    pool = _pool_req()
    for i in range(8):
        candidate = base if i == 0 else f"{base[:24]}_{secrets.token_hex(2)}"
        try:
            row = await pool.fetchrow(
                """
                INSERT INTO ad_links (slug, title, kind)
                VALUES ($1, $2, $3)
                RETURNING id, slug, title, kind, clicks, created_at, archived_at
                """,
                candidate,
                name,
                link_kind,
            )
            return dict(row)
        except asyncpg.exceptions.UniqueViolationError:
            continue
    raise ValueError("Не удалось подобрать код ссылки, задайте другой")


async def ensure_story_ad_link(
    telegram_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
) -> dict:
    tid = int(telegram_id)
    slug = f"st_{tid}"
    if len(slug) > 32:
        slug = f"st{tid}"[:32]
    if username:
        title = f"Сторис @{str(username).lstrip('@')}"[:80]
    elif first_name:
        title = f"Сторис {first_name}"[:80]
    else:
        title = f"Сторис {tid}"[:80]
    pool = _pool_req()
    row = await pool.fetchrow(
        """
        INSERT INTO ad_links (slug, title, kind)
        VALUES ($1, $2, 'story')
        ON CONFLICT (slug) DO UPDATE SET
            title = EXCLUDED.title,
            kind = 'story',
            archived_at = NULL
        RETURNING id, slug, title, kind, clicks, created_at, archived_at
        """,
        slug,
        title,
    )
    return dict(row)


async def archive_ad_link(link_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE ad_links
        SET archived_at = timezone('utc', now())
        WHERE id = $1 AND archived_at IS NULL AND COALESCE(kind, 'manual') = 'manual'
        RETURNING id
        """,
        int(link_id),
    )
    return bool(row)


async def list_ad_links(*, include_archived: bool = False, kind: str = "manual") -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT
            l.id,
            l.slug,
            l.title,
            COALESCE(l.kind, 'manual') AS kind,
            COALESCE(l.clicks, 0)::int AS clicks,
            l.created_at,
            l.archived_at,
            COUNT(u.telegram_id)::int AS users,
            COUNT(u.telegram_id) FILTER (WHERE u.trial_used)::int AS trial,
            COUNT(u.telegram_id) FILTER (WHERE COALESCE(u.has_paid_topup, FALSE))::int AS paid
        FROM ad_links l
        LEFT JOIN users u ON u.ad_link_id = l.id
        WHERE COALESCE(l.kind, 'manual') = $2
          AND ($1::bool OR l.archived_at IS NULL)
        GROUP BY l.id
        ORDER BY l.created_at DESC, l.id DESC
        """,
        bool(include_archived),
        str(kind or "manual"),
    )
    return [dict(r) for r in rows]


async def story_share_stats() -> dict:
    pool = _pool_req()
    summary = await pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE u.story_pending_at IS NOT NULL OR u.story_rewarded_at IS NOT NULL
            )::int AS shared,
            COUNT(*) FILTER (
                WHERE u.story_pending_at IS NOT NULL AND u.story_rewarded_at IS NULL
            )::int AS pending,
            COUNT(*) FILTER (WHERE u.story_rewarded_at IS NOT NULL)::int AS rewarded,
            COALESCE(SUM(COALESCE(l.clicks, 0)) FILTER (WHERE l.id IS NOT NULL), 0)::int AS clicks,
            COUNT(attr.telegram_id)::int AS users,
            COUNT(attr.telegram_id) FILTER (WHERE attr.trial_used)::int AS trial,
            COUNT(attr.telegram_id) FILTER (
                WHERE COALESCE(attr.has_paid_topup, FALSE)
            )::int AS paid
        FROM users u
        LEFT JOIN ad_links l
            ON l.slug = ('st_' || u.telegram_id::text)
           AND COALESCE(l.kind, 'manual') = 'story'
        LEFT JOIN users attr ON attr.ad_link_id = l.id
        WHERE u.story_pending_at IS NOT NULL
           OR u.story_rewarded_at IS NOT NULL
           OR l.id IS NOT NULL
        """
    )
    rows = await pool.fetch(
        """
        SELECT
            u.telegram_id,
            u.username,
            u.first_name,
            u.story_pending_at,
            u.story_rewarded_at,
            l.id AS ad_link_id,
            l.slug,
            COALESCE(l.clicks, 0)::int AS clicks,
            COUNT(attr.telegram_id)::int AS users,
            COUNT(attr.telegram_id) FILTER (WHERE attr.trial_used)::int AS trial,
            COUNT(attr.telegram_id) FILTER (
                WHERE COALESCE(attr.has_paid_topup, FALSE)
            )::int AS paid
        FROM users u
        LEFT JOIN ad_links l
            ON l.slug = ('st_' || u.telegram_id::text)
           AND COALESCE(l.kind, 'manual') = 'story'
        LEFT JOIN users attr ON attr.ad_link_id = l.id
        WHERE u.story_pending_at IS NOT NULL
           OR u.story_rewarded_at IS NOT NULL
           OR l.id IS NOT NULL
        GROUP BY u.telegram_id, l.id
        ORDER BY COALESCE(u.story_rewarded_at, u.story_pending_at, l.created_at) DESC NULLS LAST
        LIMIT 200
        """
    )
    return {"summary": dict(summary) if summary else {}, "items": [dict(r) for r in rows]}


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


async def claim_invitee_payment_bonus(telegram_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET referral_invitee_bonus_at = timezone('utc', now())
        WHERE telegram_id = $1
          AND referred_by IS NOT NULL
          AND referral_invitee_bonus_at IS NULL
          AND COALESCE(has_paid_topup, FALSE)
        RETURNING telegram_id
        """,
        int(telegram_id),
    )
    return bool(row)


async def start_story_check(telegram_id: int) -> bool:
    return False


async def approve_story_reward(telegram_id: int, amount: int) -> int | None:
    return None


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
        "UPDATE users SET accepted_legal_at = $1 WHERE telegram_id = $2 AND accepted_legal_at IS NULL",
        _utc_now(),
        telegram_id,
    )


async def mark_bot_started(telegram_id: int) -> None:
    await _pool_req().execute(
        "UPDATE users SET bot_started_at = $1 WHERE telegram_id = $2 AND bot_started_at IS NULL",
        _utc_now(), telegram_id,
    )


async def mark_legal_notice(telegram_id: int) -> None:
    await _pool_req().execute(
        "UPDATE users SET legal_notice_at = $1 WHERE telegram_id = $2 AND legal_notice_at IS NULL",
        _utc_now(), telegram_id,
    )


async def accept_legal_after_notice(telegram_id: int) -> None:
    """Record a subsequent user action, never registration or elapsed time alone."""
    await _pool_req().execute(
        """UPDATE users SET accepted_legal_at = $1
           WHERE telegram_id = $2 AND accepted_legal_at IS NULL
             AND legal_notice_at IS NOT NULL""",
        _utc_now(), telegram_id,
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
            gift_claimed_at = NOW(),
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
    await resolve_exit_feedback()
    await track_reminder_connections()
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
    await resolve_exit_feedback()
    await track_reminder_connections()


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
          AND bot_started_at IS NOT NULL AND bot_blocked_at IS NULL
          AND blocked_at IS NULL AND billing_paused_at IS NULL
          AND (
            low_balance_notified_at IS NULL
            OR low_balance_notified_at <= timezone('utc', now()) - INTERVAL '24 hours'
          )
          AND NOT EXISTS (SELECT 1 FROM message_log m WHERE m.telegram_id=users.telegram_id
              AND m.status='sent' AND m.kind IN ('low_balance','nudge_trial_end','cabinet_link','nudge_first_online')
              AND m.created_at > timezone('utc', now()) - INTERVAL '24 hours')
        RETURNING telegram_id
        """,
        telegram_id,
    )
    return row is not None


async def mark_paid_topup(telegram_id: int) -> None:
    await _pool_req().execute(
        "UPDATE users SET has_paid_topup = TRUE, checkout_started_at = NULL WHERE telegram_id = $1",
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
        "payment_nudge": _on("payment_nudge"),
        "invite_nudge": _on("invite_nudge"),
        "info_nudge": _on("info_nudge"),
        "story_nudge": False,
        "legal_nudge": _on("legal_nudge"),
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


async def user_billing_paused(telegram_id: int) -> bool:
    val = await _pool_req().fetchval(
        "SELECT billing_paused_at IS NOT NULL FROM users WHERE telegram_id = $1",
        telegram_id,
    )
    return bool(val)


async def set_user_billing_paused(telegram_id: int, paused: bool) -> bool:
    pool = _pool_req()
    if paused:
        result = await pool.execute(
            """
            UPDATE users
            SET billing_paused_at = COALESCE(billing_paused_at, $2)
            WHERE telegram_id = $1
            """,
            telegram_id,
            _utc_now(),
        )
    else:
        result = await pool.execute(
            "UPDATE users SET billing_paused_at = NULL WHERE telegram_id = $1",
            telegram_id,
        )
    return result == "UPDATE 1"


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
            # Serialize with campaign enrollment/awards and lock the parent before cleanup.
            await conn.execute('SELECT pg_advisory_xact_lock(73619420)')
            exists = await conn.fetchval("SELECT 1 FROM users WHERE telegram_id = $1 FOR UPDATE", telegram_id)
            if not exists:
                return False
            await conn.execute("DELETE FROM referral_campaign_messages WHERE telegram_id = $1", telegram_id)
            await conn.execute("DELETE FROM referral_campaign_awards WHERE referrer_id = $1", telegram_id)
            await conn.execute("DELETE FROM referral_campaign_friends WHERE invitee_id = $1 OR referrer_id = $1", telegram_id)
            await conn.execute("DELETE FROM cabinet_login_challenges WHERE telegram_id = $1", telegram_id)
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
        """
        SELECT *
        FROM devices
        WHERE telegram_id = $1
        ORDER BY CASE WHEN COALESCE(kind, '') = 'router' THEN 1 ELSE 0 END, id
        """,
        telegram_id,
    )
    return [dict(r) for r in rows]


async def add_device(
    telegram_id: int,
    title: str,
    remnawave_id: int,
    platform: str | None = None,
    client: str | None = None,
    kind: str | None = None,
) -> dict:
    row = await _pool_req().fetchrow(
        """
        INSERT INTO devices (telegram_id, title, remnawave_id, last_billed_on, last_billed_at, platform, client, kind)
        VALUES ($1, $2, $3, (timezone('utc', now()))::date, timezone('utc', now()), $4, $5, $6)
        RETURNING *
        """,
        telegram_id,
        title,
        remnawave_id,
        platform,
        client,
        str(kind or ""),
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
    async with _pool_req().acquire() as conn:
        async with conn.transaction():
            # Serialize deletions by account: only the last one creates a survey.
            await conn.fetchval("SELECT telegram_id FROM users WHERE telegram_id=$1 FOR UPDATE", telegram_id)
            await resolve_exit_feedback(conn)
            row = await conn.fetchrow(
                "DELETE FROM devices WHERE id=$1 AND telegram_id=$2 RETURNING *", device_id, telegram_id,
            )
            if not row:
                return None
            result = dict(row)
            remaining = await conn.fetchval("SELECT COUNT(*) FROM devices WHERE telegram_id=$1", telegram_id)
            if not remaining:
                token = secrets.token_urlsafe(24)
                await conn.execute("INSERT INTO device_exit_feedback (token,telegram_id) VALUES ($1,$2)", token, telegram_id)
                result["exit_feedback_token"] = token
            return result


EXIT_REASONS = {"expensive": "Дорого", "not_working": "Не работает", "not_needed": "Больше не нужен", "other": "Другое"}


_EXIT_FEEDBACK_PAUSED_SQL = """
SELECT f.telegram_id FROM device_exit_feedback f
WHERE f.reason IN ('not_working','not_needed') AND f.resolved_at IS NULL
  AND NOT EXISTS (SELECT 1 FROM device_exit_feedback newer
      WHERE newer.telegram_id=f.telegram_id AND newer.reason IS NOT NULL
        AND (newer.created_at > f.created_at OR (newer.created_at=f.created_at AND newer.token > f.token)))
  AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=f.telegram_id AND d.last_online_at > f.answered_at)
"""


async def resolve_exit_feedback(conn=None) -> None:
    await (conn or _pool_req()).execute(
        """UPDATE device_exit_feedback SET resolved_at=NOW()
        WHERE resolved_at IS NULL AND reason IN ('not_working','not_needed')
          AND EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=device_exit_feedback.telegram_id
              AND d.last_online_at > device_exit_feedback.answered_at)"""
    )


async def exit_feedback_suppressed_ids() -> list[int]:
    rows = await _pool_req().fetch(_EXIT_FEEDBACK_PAUSED_SQL)
    return [int(row['telegram_id']) for row in rows]


async def save_exit_feedback(telegram_id: int, token: str, reason: str) -> bool:
    if reason not in EXIT_REASONS:
        return False
    row = await _pool_req().fetchrow(
        """UPDATE device_exit_feedback SET reason=$3, answered_at=COALESCE(answered_at,NOW())
        WHERE token=$1 AND telegram_id=$2 AND created_at > NOW() - INTERVAL '1 day'
          AND (reason IS NULL OR reason=$3)
        RETURNING token""", token, telegram_id, reason,
    )
    return row is not None


async def admin_exit_feedback() -> dict:
    pool = _pool_req()
    counts = await pool.fetch(
        """SELECT reason, COUNT(*)::int AS n FROM device_exit_feedback
        WHERE created_at >= NOW() - INTERVAL '30 days' GROUP BY reason"""
    )
    recent = await pool.fetch(
        """SELECT f.telegram_id, u.username, f.reason, f.answered_at
        FROM device_exit_feedback f JOIN users u ON u.telegram_id=f.telegram_id
        WHERE f.reason IS NOT NULL AND f.created_at >= NOW() - INTERVAL '30 days'
        ORDER BY f.answered_at DESC LIMIT 30"""
    )
    by_reason = {r['reason']: int(r['n']) for r in counts}
    return {"total": sum(by_reason.values()), "answered": sum(n for reason,n in by_reason.items() if reason),
            "reasons": [{"key": key, "label": label, "count": by_reason.get(key,0)} for key,label in EXIT_REASONS.items()],
            "recent": [_jsonable(dict(row)) for row in recent]}


async def device_count(telegram_id: int) -> int:
    val = await _pool_req().fetchval(
        "SELECT COUNT(*) FROM devices WHERE telegram_id = $1",
        telegram_id,
    )
    return int(val or 0)


async def billable_device_count(telegram_id: int) -> int:
    val = await _pool_req().fetchval(
        """
        SELECT COUNT(*)
        FROM devices
        WHERE telegram_id = $1
          AND COALESCE(kind, '') <> 'router'
        """,
        telegram_id,
    )
    return int(val or 0)


async def get_router_device(telegram_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        """
        SELECT *
        FROM devices
        WHERE telegram_id = $1
          AND kind = 'router'
        LIMIT 1
        """,
        telegram_id,
    )
    return _as_dict(row)


async def extend_router_expire(telegram_id: int, days: int) -> datetime | None:
    n = max(1, int(days or 0))
    row = await _pool_req().fetchrow(
        """
        UPDATE users
        SET router_expire_at =
            GREATEST(
                COALESCE(router_expire_at, timezone('utc', now())),
                timezone('utc', now())
            ) + ($2::int * INTERVAL '1 day')
        WHERE telegram_id = $1
        RETURNING router_expire_at
        """,
        telegram_id,
        n,
    )
    if not row:
        return None
    return row["router_expire_at"]


async def list_router_devices() -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT d.id, d.telegram_id, d.title, d.remnawave_id, d.remnawave_uuid,
               d.panel_status, u.router_expire_at
        FROM devices d
        JOIN users u ON u.telegram_id = d.telegram_id
        WHERE d.kind = 'router'
          AND d.remnawave_id IS NOT NULL
          AND u.blocked_at IS NULL
        ORDER BY d.id
        """
    )
    return [dict(r) for r in rows]


async def devices_due_for_billing() -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT d.id, d.telegram_id, d.title, d.remnawave_id, d.remnawave_uuid,
               (u.billing_paused_at IS NOT NULL) AS billing_paused
        FROM devices d
        JOIN users u ON u.telegram_id = d.telegram_id
        WHERE d.remnawave_id IS NOT NULL
          AND COALESCE(d.kind, '') <> 'router'
          AND UPPER(COALESCE(d.panel_status, '')) <> 'DISABLED'
          AND (d.last_billed_at IS NULL OR d.last_billed_at <= timezone('utc', now()) - INTERVAL '24 hours')
          AND (d.last_billed_at IS NOT NULL OR d.last_billed_on IS NULL OR d.last_billed_on < (timezone('utc', now()))::date)
          AND u.blocked_at IS NULL
        ORDER BY d.id
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
          AND COALESCE(d.kind, '') <> 'router'
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
        SELECT d.id, d.telegram_id, d.title, d.remnawave_id, d.remnawave_uuid,
               (u.billing_paused_at IS NOT NULL) AS billing_paused
        FROM devices d
        JOIN users u ON u.telegram_id = d.telegram_id
        WHERE d.remnawave_id IS NOT NULL
          AND COALESCE(d.kind, '') <> 'router'
          AND UPPER(COALESCE(d.panel_status, '')) <> 'DISABLED'
          AND (d.last_billed_at IS NULL OR d.last_billed_at <= timezone('utc', now()) - INTERVAL '24 hours')
          AND u.blocked_at IS NULL
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
    await track_checkout(telegram_id, payment_id, pay_url)


async def track_checkout(telegram_id: int, payment_id: str | None = None, pay_url: str | None = None) -> None:
    await _pool_req().execute(
        """UPDATE users SET checkout_token = $2, checkout_started_at = NOW(),
           checkout_payment_id = $3, checkout_url = $4, checkout_nudge_at = NULL,
           first_checkout_at = COALESCE(first_checkout_at, NOW()) WHERE telegram_id = $1""",
        telegram_id, secrets.token_hex(16), payment_id, pay_url,
    )


_PAYMENT_NUDGE_DUE = """
    u.checkout_started_at <= NOW() - INTERVAL '10 minutes'
    AND u.checkout_started_at > NOW() - INTERVAL '24 hours'
    AND u.checkout_nudge_at IS NULL
    AND (u.payment_nudge_at IS NULL OR u.payment_nudge_at <= NOW() - INTERVAL '24 hours')
    AND u.bot_started_at IS NOT NULL AND u.blocked_at IS NULL AND u.bot_blocked_at IS NULL
    AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.telegram_id = u.telegram_id
                    AND p.created_at >= u.checkout_started_at)
"""


async def list_due_payment_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip_clause = " AND NOT (u.telegram_id = ANY($2::bigint[]))" if skip_ids else ""
    args = [int(limit)] + ([skip_ids] if skip_ids else [])
    rows = await _pool_req().fetch(
        f"SELECT u.* FROM users u WHERE {_PAYMENT_NUDGE_DUE}{skip_clause} ORDER BY u.checkout_started_at LIMIT $1", *args,
    )
    return [dict(row) for row in rows]


async def claim_payment_nudge(telegram_id: int, token: str) -> bool:
    row = await _pool_req().fetchrow(
        f"""UPDATE users u SET checkout_nudge_at = NOW(), payment_nudge_at = NOW()
            WHERE u.telegram_id = $1 AND u.checkout_token = $2 AND {_PAYMENT_NUDGE_DUE}
            RETURNING telegram_id""", telegram_id, token,
    )
    return row is not None


async def cancel_payment_nudge(telegram_id: int, token: str) -> None:
    await _pool_req().execute(
        "UPDATE users SET checkout_started_at = NULL WHERE telegram_id = $1 AND checkout_token = $2",
        telegram_id, token,
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
        UPDATE rollypay_orders SET status = 'granted', paid_at = NOW()
        WHERE order_id = $1 AND status <> 'granted'
        RETURNING order_id
        """,
        order_id,
    )
    return row is not None


_PROMO_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,31}$")
_PROMO_GEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def normalize_promo_code(raw: str) -> str:
    return str(raw or "").strip().upper().replace(" ", "")


def generate_promo_code() -> str:
    chunk = lambda n: "".join(secrets.choice(_PROMO_GEN_ALPHABET) for _ in range(n))
    return f"{chunk(4)}-{chunk(4)}"


async def list_promo_codes(*, include_archived: bool = False) -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT
            id, code, days, max_uses, used_count, enabled, expires_at, created_at, archived_at
        FROM promo_codes
        WHERE ($1::bool OR archived_at IS NULL)
        ORDER BY created_at DESC, id DESC
        """,
        bool(include_archived),
    )
    return [dict(r) for r in rows]


async def create_promo_code(
    *,
    code: str = "",
    days: int,
    max_uses: int | None = None,
    expires_at: datetime | None = None,
    enabled: bool = True,
) -> dict:
    day_n = int(days)
    if day_n < 1 or day_n > 3650:
        raise ValueError("Дни: от 1 до 3650")
    if max_uses is not None:
        max_uses = int(max_uses)
        if max_uses < 1:
            raise ValueError("Лимит активаций должен быть больше нуля")
    clean = normalize_promo_code(code)
    pool = _pool_req()
    for _ in range(8):
        if not clean:
            clean = generate_promo_code()
        if not _PROMO_CODE_RE.fullmatch(clean):
            raise ValueError("Код: латиница, цифры, _ и -, от 2 до 32 знаков")
        try:
            row = await pool.fetchrow(
                """
                INSERT INTO promo_codes (code, days, max_uses, expires_at, enabled)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, code, days, max_uses, used_count, enabled, expires_at, created_at, archived_at
                """,
                clean,
                day_n,
                max_uses,
                expires_at,
                bool(enabled),
            )
            return dict(row)
        except asyncpg.exceptions.UniqueViolationError:
            if code:
                raise ValueError("Такой промокод уже есть") from None
            clean = ""
            continue
    raise ValueError("Не удалось подобрать код")


async def update_promo_code(
    promo_id: int,
    *,
    days: int | None = None,
    max_uses: int | None = ...,
    expires_at: datetime | None = ...,
    enabled: bool | None = None,
) -> dict | None:
    row = await _pool_req().fetchrow(
        "SELECT * FROM promo_codes WHERE id = $1 AND archived_at IS NULL",
        int(promo_id),
    )
    if not row:
        return None
    next_days = int(row["days"] if days is None else days)
    if next_days < 1 or next_days > 3650:
        raise ValueError("Дни: от 1 до 3650")
    if max_uses is ...:
        next_max = row["max_uses"]
    elif max_uses is None:
        next_max = None
    else:
        next_max = int(max_uses)
        if next_max < 1:
            raise ValueError("Лимит активаций должен быть больше нуля")
        if next_max < int(row["used_count"] or 0):
            raise ValueError("Лимит не может быть меньше уже использованных")
    if expires_at is ...:
        next_exp = row["expires_at"]
    else:
        next_exp = expires_at
    next_enabled = bool(row["enabled"] if enabled is None else enabled)
    updated = await _pool_req().fetchrow(
        """
        UPDATE promo_codes
        SET days = $2,
            max_uses = $3,
            expires_at = $4,
            enabled = $5
        WHERE id = $1 AND archived_at IS NULL
        RETURNING id, code, days, max_uses, used_count, enabled, expires_at, created_at, archived_at
        """,
        int(promo_id),
        next_days,
        next_max,
        next_exp,
        next_enabled,
    )
    return dict(updated) if updated else None


async def archive_promo_code(promo_id: int) -> bool:
    row = await _pool_req().fetchrow(
        """
        UPDATE promo_codes
        SET archived_at = timezone('utc', now()), enabled = FALSE
        WHERE id = $1 AND archived_at IS NULL
        RETURNING id
        """,
        int(promo_id),
    )
    return bool(row)


async def claim_promo_code(telegram_id: int, code: str) -> int:
    """Activate promo for user. Returns days granted. Raises ValueError on failure."""
    clean = normalize_promo_code(code)
    if not clean:
        raise ValueError("Промокод не найден")
    pool = _pool_req()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT id, code, days, max_uses, used_count, enabled, expires_at, archived_at
                FROM promo_codes
                WHERE code = $1
                FOR UPDATE
                """,
                clean,
            )
            if not row or row["archived_at"] is not None:
                raise ValueError("Промокод не найден")
            if not row["enabled"]:
                raise ValueError("Промокод выключен")
            exp = row["expires_at"]
            if exp is not None:
                if getattr(exp, "tzinfo", None) is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp <= _utc_now():
                    raise ValueError("Срок промокода истёк")
            max_uses = row["max_uses"]
            used = int(row["used_count"] or 0)
            if max_uses is not None and used >= int(max_uses):
                raise ValueError("Лимит активаций исчерпан")
            try:
                await conn.execute(
                    "INSERT INTO promo_uses (telegram_id, code) VALUES ($1, $2)",
                    int(telegram_id),
                    clean,
                )
            except asyncpg.exceptions.UniqueViolationError:
                raise ValueError("Промокод уже использован") from None
            await conn.execute(
                """
                UPDATE promo_codes
                SET used_count = COALESCE(used_count, 0) + 1
                WHERE id = $1
                """,
                int(row["id"]),
            )
            return int(row["days"])


async def use_promo(telegram_id: int, code: str) -> bool:
    try:
        await claim_promo_code(telegram_id, code)
        return True
    except ValueError:
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
        "exit_feedback": await admin_exit_feedback(),
        "reminder_results": await admin_reminder_results(),
    }


# One set of predicates powers both counters and drill-down lists.
_FUNNEL_CTE = """
WITH all_flags AS (
    SELECT u.telegram_id, u.bot_started_at, u.referred_by,
        u.referred_by IS NOT NULL AS from_ref,
        u.ad_link_id IS NOT NULL AS from_ad,
        u.referred_by IS NULL AND u.ad_link_id IS NULL AS organic,
        u.accepted_legal_at IS NOT NULL AS legal,
        COALESCE(u.trial_used, FALSE) AS trial,
        u.blocked_at IS NOT NULL AS blocked,
        EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id) AS has_device,
        u.first_online_at IS NOT NULL AS connected,
        (u.first_checkout_at IS NOT NULL OR EXISTS (
            SELECT 1 FROM rollypay_orders o WHERE o.telegram_id=u.telegram_id)) AS checkout,
        (COALESCE(u.has_paid_topup,FALSE) OR
            EXISTS (SELECT 1 FROM rollypay_orders o WHERE o.telegram_id=u.telegram_id AND o.status='granted') OR
            EXISTS (SELECT 1 FROM payments p WHERE p.telegram_id=u.telegram_id)) AS paid,
        ((SELECT COUNT(*) FROM rollypay_orders o WHERE o.telegram_id=u.telegram_id AND o.status='granted') +
         (SELECT COUNT(*) FROM payments p WHERE p.telegram_id=u.telegram_id)) >= 2 AS repeat_paid,
        EXISTS (SELECT 1 FROM payments p WHERE p.telegram_id=u.telegram_id) AS paid_stars,
        EXISTS (SELECT 1 FROM rollypay_orders o WHERE o.telegram_id=u.telegram_id AND o.status='granted') AS paid_rollypay,
        EXISTS (SELECT 1 FROM users inv WHERE inv.referred_by=u.telegram_id AND inv.bot_started_at IS NOT NULL) AS invited,
        EXISTS (SELECT 1 FROM promo_uses p WHERE p.telegram_id=u.telegram_id) AS promo
    FROM users u
), flags AS (
    SELECT * FROM all_flags WHERE bot_started_at IS NOT NULL
        AND ($1::timestamptz IS NULL OR bot_started_at >= $1)
        AND ($2::timestamptz IS NULL OR bot_started_at < $2)
), invitees AS (
    SELECT * FROM all_flags WHERE bot_started_at IS NOT NULL
        AND referred_by IN (SELECT telegram_id FROM flags)
)
"""
_FUNNEL_PREDICATES = {
    "entered": "TRUE", "from_ref": "from_ref", "from_ad": "from_ad", "organic": "organic",
    "legal": "legal", "trial": "trial", "device": "has_device", "connected": "connected",
    "checkout": "checkout OR paid", "paid": "paid", "repeat_paid": "repeat_paid",
    "paid_stars": "paid_stars", "paid_rollypay": "paid_rollypay",
    "referred": "invited", "promo": "promo", "blocked": "blocked",
    "device_no_online": "has_device AND NOT connected",
    "checkout_drop": "checkout AND NOT paid", "no_legal": "NOT legal",
    "no_gift": "NOT trial AND NOT paid", "gift_no_online": "trial AND NOT connected",
    "online_no_paid": "connected AND NOT paid", "paid_no_repeat": "paid AND NOT repeat_paid",
    "trial_transition": "trial", "connected_transition": "trial AND connected",
    "checkout_transition": "connected AND (checkout OR paid)",
    "paid_transition": "paid", "repeat_paid_transition": "repeat_paid",
}
_FUNNEL_INV_KEYS = ("entered", "legal", "trial", "device", "connected", "checkout", "paid")
_FUNNEL_KEYS = tuple(_FUNNEL_PREDICATES) + tuple("inv_" + k for k in _FUNNEL_INV_KEYS)
_FUNNEL_SQL = _FUNNEL_CTE + "SELECT " + ",\n".join(
    [f"(SELECT COUNT(*) FROM flags WHERE {condition})::int AS {key}"
     for key, condition in _FUNNEL_PREDICATES.items()] +
    [f"(SELECT COUNT(*) FROM invitees WHERE {_FUNNEL_PREDICATES[key]})::int AS inv_{key}"
     for key in _FUNNEL_INV_KEYS]
)


def _funnel_row(row) -> dict:
    if not row:
        return {k: 0 for k in _FUNNEL_KEYS}
    return {k: int(row[k] or 0) for k in _FUNNEL_KEYS}


async def admin_funnel() -> dict:
    pool = _pool_req()
    now = await pool.fetchval("SELECT now()")

    async def window(start, end):
        row = await pool.fetchrow(_FUNNEL_SQL, start, end)
        return _funnel_row(row)

    d1 = timedelta(days=1)
    d7 = timedelta(days=7)
    d30 = timedelta(days=30)
    d90 = timedelta(days=90)
    result = {
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
    for key, duration in (("1d", d1), ("7d", d7), ("30d", d30), ("90d", d90)):
        result[key]["from"] = (now - duration).isoformat()
        result[key]["to"] = now.isoformat()
    return result


_ADMIN_TRAFFIC_SQL = """CAST(GREATEST(
    COALESCE((SELECT SUM(GREATEST(COALESCE(d.used_traffic_bytes, 0),
        COALESCE(d.lifetime_traffic_bytes, 0))) FROM devices d
        WHERE d.telegram_id = u.telegram_id), 0),
    COALESCE(u.used_traffic_bytes, 0), COALESCE(u.lifetime_traffic_bytes, 0)) AS BIGINT)"""


def _admin_users_order(extra: dict | None = None) -> str:
    return {
        "traffic_desc": "traffic_total_bytes DESC, u.telegram_id DESC",
        "traffic_asc": "traffic_total_bytes ASC, u.telegram_id DESC",
        "online_desc": "last_online_at DESC NULLS LAST, u.telegram_id DESC",
        "online_asc": "last_online_at ASC NULLS LAST, u.telegram_id DESC",
    }.get((extra or {}).get("sort"), "u.created_at DESC, u.telegram_id DESC")


def _admin_users_filter(query: str, extra: dict | None = None) -> tuple[str, list]:
    clauses: list[str] = []
    args: list = []
    q = (query or "").strip()
    extra = extra or {}
    stage = str(extra.get("funnel_step") or "")
    if stage and stage not in _FUNNEL_KEYS:
        raise ValueError("Unknown funnel stage")
    if stage in _FUNNEL_KEYS:
        invited = stage.startswith("inv_")
        key = stage[4:] if invited else stage
        start = datetime.fromisoformat(extra["funnel_from"]) if extra.get("funnel_from") else None
        end = datetime.fromisoformat(extra["funnel_to"]) if extra.get("funnel_to") else None
        args.extend([start, end])
        dataset = "invitees" if invited else "flags"
        clauses.append(f"u.telegram_id IN ({_FUNNEL_CTE} SELECT telegram_id FROM {dataset} WHERE {_FUNNEL_PREDICATES[key]})")
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
    elif status == "billing_pause":
        clauses.append("u.billing_paused_at IS NOT NULL")
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
    for key, op in (("traffic_min", ">="), ("traffic_max", "<=")):
        raw = str(extra.get(key) or "").strip()
        if not raw:
            continue
        try:
            gb = Decimal(raw.replace(",", "."))
            if not gb.is_finite() or gb < 0 or gb > 1_000_000_000:
                continue
        except InvalidOperation:
            continue
        args.append(int(gb * (1024 ** 3)))
        clauses.append(f"{_ADMIN_TRAFFIC_SQL} {op} ${len(args)}")
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
    inactive_days = {"inactive_1d": 1, "inactive_7d": 7, "inactive_30d": 30}.get(online)
    if inactive_days:
        args.append(inactive_days)
        clauses.append(f"""(SELECT MAX(d0.last_online_at) FROM devices d0
            WHERE d0.telegram_id = u.telegram_id) < NOW() - (${len(args)} * INTERVAL '1 day')""")
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
               {_ADMIN_TRAFFIC_SQL} AS traffic_total_bytes,
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
               (SELECT COUNT(*)::int FROM payments p WHERE p.telegram_id=u.telegram_id) AS stars_payment_count,
               (SELECT COALESCE(SUM(p.stars),0) FROM payments p WHERE p.telegram_id=u.telegram_id) AS paid_stars_amount,
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
        ORDER BY {_admin_users_order(extra)}
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
    """
    total = await pool.fetchval(total_sql, *args)
    rows = await pool.fetch(list_sql, *args, limit, offset)
    settings = get_settings()
    items = []
    for r in rows:
        item = _jsonable(dict(r))
        item["used_traffic_bytes"] = item.pop("traffic_total_bytes", 0)
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
          AND COALESCE(u.trial_used, FALSE) = FALSE
          AND u.bot_started_at <= timezone('utc', now()) - INTERVAL '24 hours'
          AND u.bot_blocked_at IS NULL
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
          AND u.first_online_at <= timezone('utc', now()) - INTERVAL '48 hours'
          AND u.bot_started_at IS NOT NULL AND u.bot_blocked_at IS NULL
          AND NOT (u.telegram_id = ANY($2::bigint[]))
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
        SET first_device_thanks_pending = TRUE
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
    rows = await _pool_req().fetch(
        """SELECT u.telegram_id, u.first_name, 0 AS device_nudge_count,
            EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id) AS has_device
        FROM users u
        WHERE u.blocked_at IS NULL AND u.bot_blocked_at IS NULL
          AND u.bot_started_at IS NOT NULL
          AND u.gift_claimed_at <= NOW() - INTERVAL '30 minutes'
          AND u.first_online_at IS NULL
          AND u.device_nudge_at IS NULL
          AND NOT (u.telegram_id = ANY($2::bigint[]))
        ORDER BY u.gift_claimed_at LIMIT $1""",
        int(limit), [int(x) for x in (skip_ids or [])],
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


async def list_due_legal_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    rows = await _pool_req().fetch(
        """
        SELECT u.telegram_id, u.first_name, COALESCE(u.legal_nudge_count, 0) AS legal_nudge_count
        FROM users u
        WHERE u.blocked_at IS NULL
          AND u.accepted_legal_at IS NULL
          AND COALESCE(u.legal_nudge_count, 0) < 3
          AND NOT (u.telegram_id = ANY($2::bigint[]))
          AND (
            (
              COALESCE(u.legal_nudge_count, 0) = 0
              AND u.created_at <= timezone('utc', now()) - INTERVAL '30 minutes'
              AND u.created_at > timezone('utc', now()) - INTERVAL '36 hours'
            )
            OR (
              COALESCE(u.legal_nudge_count, 0) IN (1, 2)
              AND u.legal_nudge_at IS NOT NULL
              AND u.legal_nudge_at <= timezone('utc', now()) - INTERVAL '24 hours'
            )
          )
        ORDER BY u.created_at
        LIMIT $1
        """,
        int(limit),
        skip,
    )
    return [dict(r) for r in rows]


async def mark_legal_nudge_sent(telegram_id: int) -> None:
    await _pool_req().execute(
        """
        UPDATE users
        SET legal_nudge_count = LEAST(COALESCE(legal_nudge_count, 0) + 1, 3),
            legal_nudge_at = timezone('utc', now())
        WHERE telegram_id = $1
        """,
        int(telegram_id),
    )


async def list_due_idle_nudges(limit: int = 80, skip_ids: list[int] | None = None) -> list[dict]:
    skip = [int(x) for x in (skip_ids or [])]
    rows = await _pool_req().fetch(
        """
        SELECT q.*
        FROM (
            SELECT
                u.telegram_id,
                u.first_name, u.first_online_at, u.balance_rub, u.trial_used,
                EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id) AS has_device,
                CASE
                    WHEN activity.last_seen <= timezone('utc', now()) - INTERVAL '20 days'
                         AND step.v < 20 THEN 20
                    WHEN activity.last_seen <= timezone('utc', now()) - INTERVAL '15 days'
                         AND step.v < 15 THEN 15
                    WHEN activity.last_seen <= timezone('utc', now()) - INTERVAL '10 days'
                         AND step.v < 10 THEN 10
                    WHEN activity.last_seen <= timezone('utc', now()) - INTERVAL '7 days'
                         AND step.v < 7 THEN 7
                    ELSE NULL
                END AS idle_days
            FROM users u
            LEFT JOIN (
                SELECT telegram_id, MAX(last_online_at) AS last_seen
                FROM devices
                WHERE last_online_at IS NOT NULL
                GROUP BY telegram_id
            ) seen ON seen.telegram_id = u.telegram_id
            CROSS JOIN LATERAL (
                SELECT COALESCE(seen.last_seen, u.first_online_at, u.bot_started_at) AS last_seen
            ) activity
            CROSS JOIN LATERAL (
                SELECT CASE
                    WHEN u.idle_nudge_at IS NULL OR activity.last_seen > u.idle_nudge_at
                    THEN 0
                    ELSE COALESCE(u.idle_nudge_step, 0)
                END AS v
            ) step
            WHERE u.blocked_at IS NULL
              AND u.bot_started_at IS NOT NULL AND u.bot_blocked_at IS NULL
              AND u.billing_paused_at IS NULL
              AND NOT (u.telegram_id = ANY($2::bigint[]))
        ) q
        WHERE q.idle_days IS NOT NULL
        ORDER BY q.idle_days DESC, q.telegram_id
        LIMIT $1
        """,
        int(limit),
        skip,
    )
    return [dict(r) for r in rows]


async def mark_idle_nudge_sent(telegram_id: int, days: int) -> None:
    await _pool_req().execute(
        """
        UPDATE users
        SET idle_nudge_step = $2,
            idle_nudge_at = timezone('utc', now())
        WHERE telegram_id = $1
        """,
        int(telegram_id),
        int(days),
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
                SELECT COUNT(*)::int FROM devices d WHERE d.telegram_id = u.telegram_id AND COALESCE(d.kind, '') <> 'router'
            ) AS device_count
        FROM users u
        WHERE TRUE
          AND (u.low_balance_notified_at IS NULL OR u.low_balance_notified_at <= NOW() - INTERVAL '24 hours')
          AND u.blocked_at IS NULL
          AND u.billing_paused_at IS NULL
          AND u.bot_started_at IS NOT NULL
          AND u.bot_blocked_at IS NULL
          AND COALESCE(u.balance_rub, 0) > 0
          AND EXISTS (
              SELECT 1 FROM devices d WHERE d.telegram_id = u.telegram_id AND COALESCE(d.kind, '') <> 'router'
          )
          AND COALESCE(u.balance_rub, 0) <= $3 * GREATEST(
              (SELECT COUNT(*)::int FROM devices d WHERE d.telegram_id = u.telegram_id AND COALESCE(d.kind, '') <> 'router'),
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


def _announcement_row(row) -> dict | None:
    if not row:
        return None
    data = dict(row)
    items = data.get("items")
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except ValueError:
            items = []
    if not isinstance(items, list):
        items = []
    data["items"] = [str(x).strip() for x in items if str(x).strip()]
    created = data.get("created_at")
    if created is not None and hasattr(created, "isoformat"):
        data["created_at"] = created.isoformat()
    return data


async def create_update_announcement(
    title: str,
    items: list[str],
    body: str,
    *,
    kicker: str = "",
    lead: str = "",
    closing: str = "",
    image_name: str | None = None,
) -> dict:
    row = await _pool_req().fetchrow(
        """
        INSERT INTO update_announcements (title, items, body, kicker, lead, closing, image_name)
        VALUES ($1, $2::jsonb, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        title,
        json.dumps(items, ensure_ascii=False),
        body,
        kicker,
        lead,
        closing,
        image_name,
    )
    return _announcement_row(row) or {
        "title": title,
        "items": items,
        "body": body,
        "kicker": kicker,
        "lead": lead,
        "closing": closing,
        "image_name": image_name,
    }


async def set_announcement_image(ann_id: int, image_name: str) -> dict | None:
    row = await _pool_req().fetchrow(
        """
        UPDATE update_announcements
        SET image_name = $2
        WHERE id = $1
        RETURNING *
        """,
        int(ann_id),
        image_name,
    )
    return _announcement_row(row)


async def get_update_announcement(ann_id: int) -> dict | None:
    row = await _pool_req().fetchrow(
        "SELECT * FROM update_announcements WHERE id = $1",
        int(ann_id),
    )
    return _announcement_row(row)


async def list_update_announcements(limit: int = 30) -> list[dict]:
    rows = await _pool_req().fetch(
        """
        SELECT *
        FROM update_announcements
        ORDER BY id DESC
        LIMIT $1
        """,
        max(1, min(100, int(limit))),
    )
    return [item for item in (_announcement_row(r) for r in rows) if item]


async def latest_update_announcement() -> dict | None:
    row = await _pool_req().fetchrow(
        """
        SELECT *
        FROM update_announcements
        ORDER BY id DESC
        LIMIT 1
        """
    )
    return _announcement_row(row)


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


async def issue_cabinet_token(telegram_id: int, days: int = 10, *, replace: bool = False) -> str:
    raw = secrets.token_urlsafe(32)
    expires = _utc_now() + timedelta(days=max(1, days))
    pool = _pool_req()
    if replace:
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
    await _pool_req().execute(
        "DELETE FROM cabinet_login_challenges WHERE expires_at <= timezone('utc', now())"
    )


def _ip_hash(ip: str) -> str:
    return hashlib.sha256((ip or "").encode("utf-8")).hexdigest()


async def create_cabinet_login_challenge(telegram_id: int, ip: str) -> str:
    challenge_id = secrets.token_urlsafe(16)
    expires = _utc_now() + timedelta(minutes=10)
    pool = _pool_req()
    await pool.execute(
        """
        UPDATE cabinet_login_challenges
        SET status = 'expired'
        WHERE telegram_id = $1 AND status = 'pending'
        """,
        int(telegram_id),
    )
    await pool.execute(
        """
        INSERT INTO cabinet_login_challenges (id, telegram_id, ip_hash, status, expires_at)
        VALUES ($1, $2, $3, 'pending', $4)
        """,
        challenge_id,
        int(telegram_id),
        _ip_hash(ip),
        expires,
    )
    return challenge_id


async def get_cabinet_login_challenge(challenge_id: str, ip: str | None = None) -> dict | None:
    cid = (challenge_id or "").strip()
    if not cid:
        return None
    row = await _pool_req().fetchrow(
        "SELECT * FROM cabinet_login_challenges WHERE id = $1",
        cid,
    )
    data = _as_dict(row)
    if not data:
        return None
    if ip is not None and data.get("ip_hash") and data["ip_hash"] != _ip_hash(ip):
        return None
    status = str(data.get("status") or "")
    expires = data.get("expires_at")
    if status == "pending" and expires and expires <= _utc_now():
        await _pool_req().execute(
            "UPDATE cabinet_login_challenges SET status = 'expired' WHERE id = $1 AND status = 'pending'",
            cid,
        )
        data["status"] = "expired"
    return data


async def approve_cabinet_login_challenge(challenge_id: str, telegram_id: int, days: int = 365) -> str | None:
    cid = (challenge_id or "").strip()
    row = await _pool_req().fetchrow(
        """
        SELECT * FROM cabinet_login_challenges
        WHERE id = $1 AND telegram_id = $2
        """,
        cid,
        int(telegram_id),
    )
    if not row or str(row["status"]) != "pending":
        return None
    if row["expires_at"] and row["expires_at"] <= _utc_now():
        await _pool_req().execute(
            "UPDATE cabinet_login_challenges SET status = 'expired' WHERE id = $1 AND status = 'pending'",
            cid,
        )
        return None
    token = await issue_cabinet_token(int(telegram_id), days, replace=False)
    await _pool_req().execute(
        """
        UPDATE cabinet_login_challenges
        SET status = 'approved',
            session_token = $2,
            expires_at = $3
        WHERE id = $1 AND status = 'pending'
        """,
        cid,
        token,
        _utc_now() + timedelta(minutes=10),
    )
    return token


async def decline_cabinet_login_challenge(challenge_id: str, telegram_id: int) -> bool:
    cid = (challenge_id or "").strip()
    row = await _pool_req().fetchrow(
        """
        UPDATE cabinet_login_challenges
        SET status = 'declined'
        WHERE id = $1 AND telegram_id = $2 AND status = 'pending'
        RETURNING id
        """,
        cid,
        int(telegram_id),
    )
    return row is not None


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


async def nudge_suppressed_ids(hours: int = 24) -> list[int]:
    """Persist cooldown across loop iterations and restarts; checkout has priority."""
    rows = await _pool_req().fetch(
        """SELECT u.telegram_id FROM users u
        WHERE u.bot_started_at IS NULL OR u.blocked_at IS NOT NULL OR u.bot_blocked_at IS NOT NULL
           OR u.checkout_started_at > NOW() - INTERVAL '20 minutes'
           OR EXISTS (SELECT 1 FROM message_log m WHERE m.telegram_id = u.telegram_id
               AND m.status = 'sent' AND (m.kind LIKE 'nudge_%' OR m.kind IN ('broadcast', 'low_balance'))
               AND m.created_at > NOW() - ($1 * INTERVAL '1 hour'))""", hours,
    )
    return [int(r['telegram_id']) for r in rows]


async def reward_referral_payment(invitee_id: int, payment_key: str, amount: int,
                                  *, enabled: bool, first_payment: bool) -> dict | None:
    """Record paused payments too; credit each provider payment at most once."""
    if not payment_key or amount <= 0:
        return None
    async with _pool_req().acquire() as conn:
        async with conn.transaction():
            await conn.execute('SELECT pg_advisory_xact_lock(73619420)')
            invitee = await conn.fetchrow(
                "SELECT referred_by, referral_rewarded FROM users WHERE telegram_id=$1 FOR UPDATE", invitee_id)
            if not invitee:
                return None
            referrer_id = invitee['referred_by']
            inserted = await conn.fetchrow(
                """INSERT INTO referral_payment_rewards (payment_key, invitee_id, referrer_id, topup_rub, enabled)
                   VALUES ($1,$2,$3,$4,$5) ON CONFLICT (payment_key) DO NOTHING RETURNING payment_key""",
                payment_key, invitee_id, referrer_id, amount, enabled)
            if not inserted:
                return None
            campaign = await _reward_campaign(conn, invitee_id, referrer_id, payment_key, first_payment)
            if not enabled or not referrer_id or referrer_id == invitee_id:
                return {'referrer_id': referrer_id, 'amount': 0, 'campaign': campaign} if campaign else None
            referrer = await conn.fetchrow(
                "SELECT referral_fraction FROM users WHERE telegram_id=$1 FOR UPDATE", referrer_id)
            if not referrer:
                return None
            percent, fraction = divmod(amount * 5 + int(referrer['referral_fraction'] or 0), 100)
            bonus = 50 if first_payment and not invitee['referral_rewarded'] else 0
            reward = bonus + percent
            after = await conn.fetchval(
                """UPDATE users SET balance_rub=COALESCE(balance_rub,0)+$2,
                   referral_earned=COALESCE(referral_earned,0)+$2, referral_fraction=$3,
                   low_balance_notified_at=CASE WHEN $2 > 0 THEN NULL ELSE low_balance_notified_at END
                   WHERE telegram_id=$1 RETURNING balance_rub""", referrer_id, reward, fraction)
            if bonus:
                await conn.execute("UPDATE users SET referral_rewarded=TRUE WHERE telegram_id=$1", invitee_id)
            await conn.execute("UPDATE referral_payment_rewards SET reward_rub=$2 WHERE payment_key=$1", payment_key,reward)
            if reward:
                await conn.execute(
                    """INSERT INTO billing_events (telegram_id,kind,source,amount,balance_after,note)
                       VALUES ($1,'referral','payment',$2,$3,$4)""", referrer_id,reward,after,
                    f"Друг {invitee_id}: первая оплата {bonus} ₽ + 5% от {amount} ₽; {payment_key}")
            return {'referrer_id':referrer_id,'amount':reward,'bonus':bonus,'percent':percent,'campaign':campaign}


async def nudge_delivery_allowed(telegram_id: int, kind: str) -> bool:
    """Respect exit preferences and retry limits, including direct sender calls."""
    if kind.startswith("nudge_") or kind == "low_balance":
        paused = await _pool_req().fetchval(
            f"SELECT EXISTS ({_EXIT_FEEDBACK_PAUSED_SQL} AND f.telegram_id=$1)", telegram_id,
        )
        if paused:
            return False
    return bool(await _pool_req().fetchval(
        """SELECT COUNT(*) < 3
            AND COALESCE(MAX(created_at + GREATEST(120,
                COALESCE((extra->>'retry_after')::int, 120)) * INTERVAL '1 second') <= NOW(), TRUE)
            AND NOT COALESCE(BOOL_OR(COALESCE((extra->>'permanent')::boolean, FALSE)), FALSE)
        FROM message_log WHERE telegram_id=$1 AND kind=$2 AND status='failed'
          AND created_at > NOW() - INTERVAL '24 hours'""", telegram_id, kind,
    ))


async def release_payment_nudge(telegram_id: int, token: str) -> None:
    await _pool_req().execute(
        """UPDATE users SET checkout_nudge_at=NULL, payment_nudge_at=NULL
        WHERE telegram_id=$1 AND checkout_token=$2""", telegram_id, token,
    )


async def nudge_retry_suppressed_ids() -> list[int]:
    """Exclude recipients before batching so failed chats cannot starve the queue."""
    rows = await _pool_req().fetch(
        """SELECT DISTINCT telegram_id FROM message_log
        WHERE status='failed' AND created_at > NOW() - INTERVAL '24 hours'
          AND (kind LIKE 'nudge_%' OR kind='first_device_thanks')
        GROUP BY telegram_id, kind
        HAVING COUNT(*) >= 3
            OR MAX(created_at + GREATEST(120, COALESCE((extra->>'retry_after')::int, 120))
                * INTERVAL '1 second') > NOW()
            OR BOOL_OR(COALESCE((extra->>'permanent')::boolean, FALSE))"""
    )
    return [int(row['telegram_id']) for row in rows if row['telegram_id'] is not None]


async def release_low_balance_notice(telegram_id: int) -> None:
    await _pool_req().execute("UPDATE users SET low_balance_notified_at=NULL WHERE telegram_id=$1", telegram_id)


async def create_reminder_delivery(telegram_id: int, kind: str, title: str, body: str) -> str:
    token=secrets.token_urlsafe(18)
    await _pool_req().execute(
        "INSERT INTO reminder_deliveries (token,telegram_id,kind,title,body) VALUES ($1,$2,$3,$4,$5)",
        token,telegram_id,kind,title,body,
    )
    return token


async def finish_reminder_delivery(token: str, status: str, message_id: int | None) -> None:
    await _pool_req().execute(
        """UPDATE reminder_deliveries SET status=$2,message_id=$3,
        sent_at=CASE WHEN $2='sent' THEN NOW() ELSE NULL END WHERE token=$1""",token,status,message_id,
    )


async def record_reminder_click(telegram_id: int, *, token: str | None = None, message_id: int | None = None) -> None:
    await _pool_req().execute(
        """WITH clicked AS (
            UPDATE reminder_deliveries SET clicked_at=COALESCE(clicked_at,NOW())
            WHERE telegram_id=$1 AND status='sent'
              AND (($2::text IS NOT NULL AND token=$2) OR ($3::bigint IS NOT NULL AND message_id=$3))
              AND sent_at >= NOW() - INTERVAL '30 days' RETURNING token
        ) INSERT INTO reminder_clicks (token) SELECT token FROM clicked""",telegram_id,token,message_id,
    )


_REMINDER_CLICKS_SQL = """
WITH clicks AS (
    SELECT c.id,c.token,c.clicked_at,r.telegram_id FROM reminder_clicks c
    JOIN reminder_deliveries r ON r.token=c.token WHERE r.status='sent'
)
"""


async def track_reminder_connections() -> None:
    try:
        await _pool_req().execute(_REMINDER_CLICKS_SQL + """
        UPDATE reminder_deliveries SET connected_at=(
            SELECT MIN(d.last_online_at) FROM devices d JOIN clicks c ON c.telegram_id=d.telegram_id
            WHERE c.token=reminder_deliveries.token
              AND d.last_online_at >= c.clicked_at AND d.last_online_at <= c.clicked_at + INTERVAL '7 days'
              AND NOT EXISTS (SELECT 1 FROM clicks later WHERE later.telegram_id=c.telegram_id
                  AND (later.clicked_at > c.clicked_at OR (later.clicked_at=c.clicked_at AND later.id>c.id))
                  AND later.clicked_at <= d.last_online_at)
        ) WHERE status='sent' AND clicked_at IS NOT NULL AND connected_at IS NULL
            AND created_at >= NOW() - INTERVAL '38 days'""")

    except Exception:
        logging.getLogger("rm-shop.db").debug("Reminder connection tracking failed", exc_info=True)

_REMINDER_RESULTS_SQL = _REMINDER_CLICKS_SQL.rstrip() + """,
payments_seen AS (
    SELECT telegram_id, created_at AS paid_at FROM payments
    UNION ALL SELECT telegram_id, paid_at FROM rollypay_orders WHERE status='granted' AND paid_at IS NOT NULL
), results AS (
    SELECT r.*, EXISTS (SELECT 1 FROM payments_seen p JOIN clicks c ON c.telegram_id=p.telegram_id
        WHERE c.token=r.token AND p.paid_at >= c.clicked_at AND p.paid_at <= c.clicked_at + INTERVAL '7 days'
        AND NOT EXISTS (SELECT 1 FROM clicks later WHERE later.telegram_id=c.telegram_id
            AND (later.clicked_at > c.clicked_at OR (later.clicked_at=c.clicked_at AND later.id>c.id))
            AND later.clicked_at <= p.paid_at)) AS paid_after
    FROM reminder_deliveries r WHERE r.created_at >= NOW() - INTERVAL '30 days'
)
"""


async def admin_reminder_results() -> dict:
    pool=_pool_req()
    grouped=await pool.fetch(_REMINDER_RESULTS_SQL + """
        SELECT kind, COUNT(*) FILTER (WHERE status='sent')::int AS sent,
          COUNT(*) FILTER (WHERE status='failed')::int AS failed,
          COUNT(DISTINCT telegram_id) FILTER (WHERE status='sent')::int AS recipients,
          COUNT(DISTINCT telegram_id) FILTER (WHERE status='sent' AND clicked_at IS NOT NULL)::int AS clicked,
          COUNT(DISTINCT telegram_id) FILTER (WHERE connected_at IS NOT NULL)::int AS connected,
          COUNT(DISTINCT telegram_id) FILTER (WHERE paid_after)::int AS paid
        FROM results GROUP BY kind ORDER BY sent DESC,kind""")
    recent=await pool.fetch(_REMINDER_RESULTS_SQL + """
        SELECT telegram_id,kind,title,body,created_at,status,clicked_at,connected_at,paid_after
        FROM results ORDER BY created_at DESC LIMIT 30""")
    return {"groups":[dict(row) for row in grouped],"recent":[_jsonable(dict(row)) for row in recent]}


async def admin_referral_campaigns() -> list[dict]:
    rows = await _pool_req().fetch("""
        SELECT c.*,
          (SELECT COUNT(*) FROM referral_campaign_friends f WHERE f.campaign_id=c.id) AS friends,
          (SELECT COUNT(*) FROM referral_campaign_awards a WHERE a.campaign_id=c.id) AS awards,
          (SELECT COUNT(*) FROM referral_campaign_messages m WHERE m.campaign_id=c.id AND m.status='sent') AS sent,
          (SELECT COUNT(*) FROM referral_campaign_messages m WHERE m.campaign_id=c.id AND m.status='failed') AS failed,
          (SELECT COUNT(*) FROM referral_campaign_messages m WHERE m.campaign_id=c.id AND m.status IN ('pending','sending')) AS pending
        FROM referral_campaigns c ORDER BY c.id DESC LIMIT 20""")
    return [_jsonable(dict(r)) for r in rows]


async def change_referral_campaign(action: str, campaign_id: int | None = None,
                                   scheduled_at: datetime | None = None) -> None:
    if action not in ('start', 'stop', 'schedule', 'cancel_schedule', 'scheduled_start'):
        raise ValueError('Неизвестное действие')
    settings = get_settings()
    if action in ('start', 'schedule') and (not settings.balance_enabled or settings.vpn_day_price_rub <= 0):
        raise ValueError('Акция доступна при оплате с баланса и положительной цене дня')
    async with _pool_req().acquire() as conn:
        async with conn.transaction():
            await conn.execute('SELECT pg_advisory_xact_lock(73619420)')
            if action == 'cancel_schedule':
                await conn.execute('DELETE FROM referral_campaign_schedule WHERE id=1')
                return
            if action == 'schedule':
                if scheduled_at is None or scheduled_at <= _utc_now():
                    raise ValueError('Выберите дату и время в будущем по МСК')
                if await conn.fetchval('SELECT id FROM referral_campaigns WHERE stopped_at IS NULL'):
                    raise ValueError('Сначала завершите текущую акцию')
                await conn.execute("""INSERT INTO referral_campaign_schedule (id,scheduled_at) VALUES (1,$1)
                    ON CONFLICT (id) DO UPDATE SET scheduled_at=excluded.scheduled_at""", scheduled_at)
                return
            if action == 'scheduled_start':
                due = await conn.fetchval("""DELETE FROM referral_campaign_schedule
                    WHERE id=1 AND scheduled_at <= $1 RETURNING scheduled_at""", _utc_now())
                if due is None:
                    return
                if not settings.balance_enabled or settings.vpn_day_price_rub <= 0:
                    raise ValueError('Нельзя запустить акцию: проверьте режим баланса и цену дня')
                action = 'start'
            if action == 'start':
                await conn.execute('DELETE FROM referral_campaign_schedule WHERE id=1')
                new_id = await conn.fetchval("""INSERT INTO referral_campaigns (reward_rub)
                    SELECT $1 WHERE NOT EXISTS
                    (SELECT 1 FROM referral_campaigns WHERE stopped_at IS NULL) RETURNING id""",
                    int(settings.vpn_day_price_rub) * 30 * 3)
                if new_id:
                    await conn.execute("""INSERT INTO referral_campaign_messages (campaign_id,telegram_id)
                        SELECT $1,telegram_id FROM users WHERE bot_started_at IS NOT NULL
                        AND blocked_at IS NULL AND bot_blocked_at IS NULL""", new_id)
            else:
                await conn.execute("""UPDATE referral_campaigns SET stopped_at=clock_timestamp()
                    WHERE id=$1 AND stopped_at IS NULL""", campaign_id)
                await conn.execute("""UPDATE referral_campaign_messages SET status='cancelled'
                    WHERE campaign_id=$1 AND status='pending'""", campaign_id)


async def _reward_campaign(conn, invitee_id: int, referrer_id: int | None,
                           payment_key: str, first_payment: bool) -> dict | None:
    # Caller holds the campaign advisory lock and provider-payment deduplication row.
    if not first_payment or not referrer_id or referrer_id == invitee_id:
        return None
    campaign = await conn.fetchrow('SELECT * FROM referral_campaigns WHERE stopped_at IS NULL')
    if not campaign:
        return None
    inserted = await conn.fetchval("""INSERT INTO referral_campaign_friends
        (invitee_id,campaign_id,referrer_id,payment_key) VALUES ($1,$2,$3,$4)
        ON CONFLICT DO NOTHING RETURNING invitee_id""",
        invitee_id, campaign['id'], referrer_id, payment_key)
    if not inserted:
        return None
    count = await conn.fetchval("""SELECT COUNT(*) FROM referral_campaign_friends
        WHERE campaign_id=$1 AND referrer_id=$2""", campaign['id'], referrer_id)
    if count < 3:
        return None
    amount = await conn.fetchval("""INSERT INTO referral_campaign_awards (campaign_id,referrer_id,amount)
        VALUES ($1,$2,$3) ON CONFLICT DO NOTHING RETURNING amount""",
        campaign['id'], referrer_id, campaign['reward_rub'])
    if amount is None:
        return None
    balance = await conn.fetchval("""UPDATE users SET balance_rub=COALESCE(balance_rub,0)+$2,
        low_balance_notified_at=NULL WHERE telegram_id=$1 RETURNING balance_rub""", referrer_id, amount)
    await conn.execute("""INSERT INTO billing_events (telegram_id,kind,source,amount,balance_after,note)
        VALUES ($1,'referral','campaign',$2,$3,$4)""", referrer_id, amount, balance,
        f"Акция #{campaign['id']}: 3 друга, 30 дней на 3 устройства")
    return {'referrer_id': referrer_id, 'amount': amount, 'campaign_id': campaign['id']}


async def claim_campaign_message() -> dict | None:
    await _pool_req().execute("""UPDATE referral_campaign_messages m SET status='cancelled'
        WHERE (m.status='pending' OR (m.status='sending' AND m.retry_at <= NOW()))
          AND (EXISTS (SELECT 1 FROM referral_campaigns c WHERE c.id=m.campaign_id AND c.stopped_at IS NOT NULL)
            OR EXISTS (SELECT 1 FROM users u WHERE u.telegram_id=m.telegram_id
                AND (u.blocked_at IS NOT NULL OR u.bot_blocked_at IS NOT NULL)))""")
    row = await _pool_req().fetchrow("""
        WITH next AS (
            SELECT m.campaign_id,m.telegram_id FROM referral_campaign_messages m
            JOIN referral_campaigns c ON c.id=m.campaign_id
            JOIN users u ON u.telegram_id=m.telegram_id
            WHERE c.stopped_at IS NULL AND m.status IN ('pending','sending')
              AND m.retry_at <= NOW() AND u.blocked_at IS NULL AND u.bot_blocked_at IS NULL
            ORDER BY m.retry_at,m.telegram_id FOR UPDATE OF m SKIP LOCKED LIMIT 1
        ), claimed AS (
            UPDATE referral_campaign_messages m SET status='sending',attempts=attempts+1,
                retry_at=NOW()+INTERVAL '5 minutes'
            FROM next n WHERE m.campaign_id=n.campaign_id AND m.telegram_id=n.telegram_id
            RETURNING m.*
        ) SELECT claimed.*,c.reward_rub FROM claimed JOIN referral_campaigns c ON c.id=claimed.campaign_id
    """)
    return dict(row) if row else None


async def finish_campaign_message(campaign_id: int, telegram_id: int, *, error: str | None = None,
                                  retry_seconds: int | None = None) -> None:
    await _pool_req().execute("""UPDATE referral_campaign_messages
        SET status=$3,error=$4,sent_at=CASE WHEN $3='sent' THEN NOW() ELSE NULL END,
            retry_at=NOW()+($5 * INTERVAL '1 second')
        WHERE campaign_id=$1 AND telegram_id=$2""", campaign_id,telegram_id,
        'sent' if error is None else 'pending' if retry_seconds is not None else 'failed',
        error, retry_seconds or 0)


async def get_referral_campaign_schedule() -> str | None:
    value = await _pool_req().fetchval('SELECT scheduled_at FROM referral_campaign_schedule WHERE id=1')
    return value.isoformat() if value else None


_CAMPAIGN_PROGRESS_SQL = """
    SELECT f.referrer_id,COUNT(*) AS friends,
        COALESCE(SUM(p.topup_rub),0) AS paid_rub,
        MAX(f.created_at) AS last_payment_at
    FROM referral_campaign_friends f
    LEFT JOIN referral_payment_rewards p ON p.payment_key=f.payment_key
    WHERE f.campaign_id=$1 GROUP BY f.referrer_id
"""


async def admin_referral_campaign_stats(campaign_id: int, page: int = 1) -> dict:
    pool = _pool_req()
    campaign = await pool.fetchrow('SELECT * FROM referral_campaigns WHERE id=$1', campaign_id)
    if not campaign:
        raise ValueError('Акция не найдена')
    summary = await pool.fetchrow("WITH progress AS (" + _CAMPAIGN_PROGRESS_SQL + """)
        SELECT COUNT(*) AS participants,
          COUNT(*) FILTER (WHERE friends=1) AS one_friend,
          COUNT(*) FILTER (WHERE friends=2) AS two_friends,
          COUNT(*) FILTER (WHERE friends>=3) AS completed,
          COALESCE(SUM(friends),0) AS friends,
          COALESCE(SUM(paid_rub),0) AS paid_rub FROM progress""", campaign_id)
    awards = await pool.fetchrow("""SELECT COUNT(*) AS awards,COALESCE(SUM(amount),0) AS awarded_rub
        FROM referral_campaign_awards WHERE campaign_id=$1""", campaign_id)
    delivery = await pool.fetchrow("""SELECT COUNT(*) AS recipients,
        COUNT(*) FILTER (WHERE status='sent') AS sent,
        COUNT(*) FILTER (WHERE status IN ('pending','sending')) AS pending,
        COUNT(*) FILTER (WHERE status='failed') AS failed,
        COUNT(*) FILTER (WHERE status='cancelled') AS cancelled
        FROM referral_campaign_messages WHERE campaign_id=$1""", campaign_id)
    page = max(1,page)
    rows = await pool.fetch("WITH progress AS (" + _CAMPAIGN_PROGRESS_SQL + """)
        SELECT p.*,u.first_name,u.username,COALESCE(a.amount,0) AS award_rub,a.created_at AS awarded_at
        FROM progress p JOIN users u ON u.telegram_id=p.referrer_id
        LEFT JOIN referral_campaign_awards a ON a.campaign_id=$1 AND a.referrer_id=p.referrer_id
        ORDER BY p.friends DESC,p.last_payment_at DESC,p.referrer_id
        LIMIT 50 OFFSET $2""",campaign_id,(page-1)*50)
    return {'campaign':_jsonable(dict(campaign)), 'summary':{key:int(value) for key,value in dict(summary).items()},
            'awards':dict(awards),'delivery':dict(delivery),
            'items':[_jsonable(dict(row)) for row in rows], 'page':page,'limit':50}
