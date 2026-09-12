CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    accepted_legal_at TIMESTAMPTZ,
    trial_used BOOLEAN NOT NULL DEFAULT FALSE,
    referred_by BIGINT,
    referral_rewarded BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remnawave_id BIGINT,
    remnawave_uuid TEXT,
    expire_at TIMESTAMPTZ,
    panel_status TEXT,
    subscription_url TEXT,
    last_synced_at TIMESTAMPTZ,
    balance_days INTEGER NOT NULL DEFAULT 0,
    balance_rub INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS users_remnawave_uuid_uidx
    ON users (remnawave_uuid)
    WHERE remnawave_uuid IS NOT NULL;

CREATE TABLE IF NOT EXISTS payments (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    plan_code TEXT NOT NULL,
    stars INTEGER NOT NULL DEFAULT 0,
    telegram_payment_id TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devices (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    title TEXT NOT NULL,
    remnawave_id BIGINT,
    remnawave_uuid TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_billed_on DATE,
    platform TEXT,
    client TEXT
);

CREATE TABLE IF NOT EXISTS promo_uses (
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    code TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (telegram_id, code)
);

CREATE TABLE IF NOT EXISTS rollypay_orders (
    order_id TEXT PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    plan_code TEXT NOT NULL,
    payment_id TEXT,
    pay_url TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rollypay_orders_payment_id_idx
    ON rollypay_orders (payment_id);

CREATE TABLE IF NOT EXISTS vpn_reports (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    username TEXT,
    first_name TEXT,
    expire_at TIMESTAMPTZ,
    panel_status TEXT,
    subscription_url TEXT,
    remnawave_uuid TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE vpn_reports ADD COLUMN IF NOT EXISTS payload JSONB;
CREATE INDEX IF NOT EXISTS vpn_reports_created_at_idx ON vpn_reports (created_at DESC);

ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_rub INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS has_paid_topup BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_billed_on DATE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_billed_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS platform TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS client TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS subscription_url TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_online_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS expire_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS panel_status TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS used_traffic_bytes BIGINT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS lifetime_traffic_bytes BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS used_traffic_bytes BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS lifetime_traffic_bytes BIGINT;

CREATE INDEX IF NOT EXISTS devices_last_billed_at_idx
    ON devices (last_billed_at)
    WHERE remnawave_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS devices_telegram_id_idx
    ON devices (telegram_id);

CREATE INDEX IF NOT EXISTS users_last_synced_idx
    ON users (last_synced_at NULLS FIRST, telegram_id);

CREATE TABLE IF NOT EXISTS app_flags (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO app_flags (key, value) VALUES
    ('trial_nudge', '1'),
    ('invite_nudge', '1'),
    ('info_nudge', '1'),
    ('story_nudge', '1')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS trust_loans (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    amount INTEGER NOT NULL,
    taken_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_at TIMESTAMPTZ NOT NULL,
    collected_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS trust_loans_due_idx
    ON trust_loans (due_at)
    WHERE collected_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS trust_loans_open_uidx
    ON trust_loans (telegram_id)
    WHERE collected_at IS NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS story_rewarded_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS story_pending_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_reason TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS bot_blocked_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_clawback_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_nudge_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_nudge_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS info_nudge_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS story_nudge_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS low_balance_notified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_device_thanks_pending BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_device_thanks_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS device_nudge_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS device_nudge_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_online_nudge_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_end_nudge_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_intro_sent_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS users_device_nudge_idx
    ON users (device_nudge_count, created_at)
    WHERE blocked_at IS NULL AND device_nudge_count < 3;

CREATE TABLE IF NOT EXISTS ad_links (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    clicks INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    archived_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ad_links_created_idx ON ad_links (created_at DESC);

ALTER TABLE users ADD COLUMN IF NOT EXISTS ad_link_id BIGINT REFERENCES ad_links (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS users_ad_link_idx
    ON users (ad_link_id)
    WHERE ad_link_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS cabinet_tokens (
    token_hash TEXT PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS cabinet_tokens_tg_idx ON cabinet_tokens (telegram_id);
CREATE INDEX IF NOT EXISTS cabinet_tokens_expires_idx ON cabinet_tokens (expires_at);

CREATE TABLE IF NOT EXISTS billing_events (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'cron',
    amount INTEGER NOT NULL DEFAULT 0,
    balance_after INTEGER,
    device_id BIGINT,
    device_title TEXT,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS billing_events_created_idx ON billing_events (created_at DESC);
CREATE INDEX IF NOT EXISTS billing_events_tg_idx ON billing_events (telegram_id, created_at DESC);
CREATE INDEX IF NOT EXISTS billing_events_device_kind_idx ON billing_events (device_id, kind, created_at DESC);
CREATE INDEX IF NOT EXISTS users_blocked_at_idx ON users (blocked_at) WHERE blocked_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS users_bot_blocked_idx ON users (bot_blocked_at) WHERE bot_blocked_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS users_trial_nudge_idx ON users (created_at)
    WHERE trial_nudge_sent_at IS NULL AND trial_used = FALSE;
CREATE INDEX IF NOT EXISTS users_invite_nudge_idx ON users (created_at)
    WHERE invite_nudge_sent_at IS NULL;
CREATE INDEX IF NOT EXISTS users_info_nudge_idx ON users (created_at)
    WHERE info_nudge_sent_at IS NULL;
CREATE INDEX IF NOT EXISTS users_story_nudge_idx ON users (telegram_id)
    WHERE story_nudge_sent_at IS NULL AND story_rewarded_at IS NULL;

UPDATE users SET has_paid_topup = TRUE
WHERE telegram_id IN (
    SELECT DISTINCT telegram_id FROM rollypay_orders WHERE status = 'granted'
)
OR telegram_id IN (
    SELECT DISTINCT telegram_id FROM payments
);

UPDATE devices
SET last_billed_at = timezone('utc', now())
WHERE last_billed_at IS NULL
  AND last_billed_on IS NOT NULL
  AND last_billed_on = (timezone('utc', now()))::date;

UPDATE devices
SET last_billed_at = (last_billed_on::timestamp AT TIME ZONE 'utc')
WHERE last_billed_at IS NULL
  AND last_billed_on IS NOT NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_earned INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_withdrawn INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_online_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS users_first_online_nudge_idx ON users (first_online_at)
    WHERE first_online_nudge_at IS NULL
      AND blocked_at IS NULL
      AND COALESCE(has_paid_topup, FALSE) = FALSE;
CREATE INDEX IF NOT EXISTS users_trial_end_nudge_idx ON users (trial_end_nudge_at, balance_rub)
    WHERE trial_end_nudge_at IS NULL
      AND blocked_at IS NULL
      AND COALESCE(has_paid_topup, FALSE) = FALSE;

UPDATE users u
SET first_online_at = s.seen
FROM (
    SELECT telegram_id, MIN(last_online_at) AS seen
    FROM devices
    WHERE last_online_at IS NOT NULL
    GROUP BY telegram_id
) s
WHERE u.telegram_id = s.telegram_id
  AND u.first_online_at IS NULL;

UPDATE users
SET first_online_at = COALESCE(last_synced_at, timezone('utc', now()))
WHERE first_online_at IS NULL
  AND COALESCE(lifetime_traffic_bytes, 0) > 0;

CREATE TABLE IF NOT EXISTS referral_payouts (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    amount INTEGER NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by BIGINT
);

CREATE INDEX IF NOT EXISTS referral_payouts_status_idx
    ON referral_payouts (status, created_at DESC);

CREATE INDEX IF NOT EXISTS referral_payouts_user_idx
    ON referral_payouts (telegram_id, created_at DESC);

CREATE TABLE IF NOT EXISTS message_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    kind TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'auto',
    telegram_id BIGINT,
    username TEXT,
    first_name TEXT,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'sent',
    extra JSONB
);

CREATE INDEX IF NOT EXISTS message_log_created_idx ON message_log (created_at DESC);
CREATE INDEX IF NOT EXISTS message_log_kind_idx ON message_log (kind, created_at DESC);
CREATE INDEX IF NOT EXISTS message_log_tg_idx ON message_log (telegram_id, created_at DESC);
CREATE INDEX IF NOT EXISTS message_log_source_idx ON message_log (source, created_at DESC);

UPDATE users u
SET bot_blocked_at = m.first_at
FROM (
    SELECT telegram_id, MIN(created_at) AS first_at
    FROM message_log
    WHERE status = 'failed'
      AND telegram_id IS NOT NULL
      AND (
        extra->>'error' = 'пользователь заблокировал бота'
        OR COALESCE(extra->>'error_raw', '') ILIKE '%blocked by the user%'
      )
    GROUP BY telegram_id
) m
WHERE u.telegram_id = m.telegram_id
  AND u.bot_blocked_at IS NULL;

CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id) ON DELETE CASCADE,
    username TEXT,
    first_name TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS tickets_status_idx ON tickets (status, last_message_at DESC);
CREATE INDEX IF NOT EXISTS tickets_user_idx ON tickets (telegram_id, last_message_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS tickets_one_open_idx
    ON tickets (telegram_id)
    WHERE status <> 'closed';

CREATE TABLE IF NOT EXISTS ticket_messages (
    id BIGSERIAL PRIMARY KEY,
    ticket_id BIGINT NOT NULL REFERENCES tickets (id) ON DELETE CASCADE,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS ticket_messages_ticket_idx ON ticket_messages (ticket_id, id);

CREATE TABLE IF NOT EXISTS ticket_attachments (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES ticket_messages (id) ON DELETE CASCADE,
    stored_name TEXT NOT NULL,
    original_name TEXT NOT NULL DEFAULT '',
    mime TEXT NOT NULL DEFAULT 'application/octet-stream',
    kind TEXT NOT NULL DEFAULT 'file',
    size_bytes INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS ticket_attachments_msg_idx ON ticket_attachments (message_id, id);

ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_invitee_bonus_at TIMESTAMPTZ;

ALTER TABLE users ADD COLUMN IF NOT EXISTS idle_nudge_step INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS idle_nudge_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS users_idle_nudge_idx
    ON users (idle_nudge_step)
    WHERE blocked_at IS NULL AND idle_nudge_step < 20;

DROP TABLE IF EXISTS auto_topups;

ALTER TABLE users ADD COLUMN IF NOT EXISTS router_expire_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS devices_one_router_uidx
    ON devices (telegram_id)
    WHERE kind = 'router';

CREATE TABLE IF NOT EXISTS update_announcements (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    items JSONB NOT NULL DEFAULT '[]',
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS update_announcements_created_idx
    ON update_announcements (created_at DESC);

ALTER TABLE update_announcements ADD COLUMN IF NOT EXISTS kicker TEXT NOT NULL DEFAULT '';
ALTER TABLE update_announcements ADD COLUMN IF NOT EXISTS lead TEXT NOT NULL DEFAULT '';
ALTER TABLE update_announcements ADD COLUMN IF NOT EXISTS closing TEXT NOT NULL DEFAULT '';
ALTER TABLE update_announcements ADD COLUMN IF NOT EXISTS image_name TEXT;


