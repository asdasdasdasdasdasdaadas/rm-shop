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

CREATE TABLE IF NOT EXISTS promo_codes (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    days INTEGER NOT NULL CHECK (days > 0),
    max_uses INTEGER,
    used_count INTEGER NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    archived_at TIMESTAMPTZ,
    CONSTRAINT promo_codes_max_uses_chk CHECK (max_uses IS NULL OR max_uses > 0)
);

CREATE INDEX IF NOT EXISTS promo_codes_active_idx
    ON promo_codes (code)
    WHERE archived_at IS NULL;

-- Orders and receipts of the previous payment provider move to neutral names; does nothing once done.
DO $$
DECLARE old_name TEXT := 'rollypay';
BEGIN
    IF to_regclass(old_name || '_orders') IS NOT NULL AND to_regclass('pay_orders') IS NULL THEN
        EXECUTE format('ALTER TABLE %I RENAME TO pay_orders', old_name || '_orders');
    END IF;
    IF to_regclass(old_name || '_orders_pkey') IS NOT NULL THEN
        EXECUTE format('ALTER INDEX %I RENAME TO pay_orders_pkey', old_name || '_orders_pkey');
    END IF;
    IF to_regclass(old_name || '_orders_payment_id_idx') IS NOT NULL THEN
        EXECUTE format('ALTER INDEX %I RENAME TO pay_orders_payment_id_idx', old_name || '_orders_payment_id_idx');
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = old_name || '_orders_telegram_id_fkey') THEN
        EXECUTE format('ALTER TABLE pay_orders RENAME CONSTRAINT %I TO pay_orders_telegram_id_fkey',
                       old_name || '_orders_telegram_id_fkey');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS pay_orders (
    order_id TEXT PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    plan_code TEXT NOT NULL,
    payment_id TEXT,
    pay_url TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS pay_orders_payment_id_idx
    ON pay_orders (payment_id);

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
    ('story_nudge', '1'),
    ('legal_nudge', '1')
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
ALTER TABLE users ADD COLUMN IF NOT EXISTS legal_nudge_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS legal_nudge_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_online_nudge_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_end_nudge_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_intro_sent_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS users_device_nudge_idx
    ON users (device_nudge_count, created_at)
    WHERE blocked_at IS NULL AND device_nudge_count < 3;
CREATE INDEX IF NOT EXISTS users_legal_nudge_idx
    ON users (legal_nudge_count, created_at)
    WHERE blocked_at IS NULL
      AND accepted_legal_at IS NULL
      AND legal_nudge_count < 3;

CREATE TABLE IF NOT EXISTS ad_links (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    clicks INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    archived_at TIMESTAMPTZ
);

ALTER TABLE ad_links ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'manual';

CREATE INDEX IF NOT EXISTS ad_links_created_idx ON ad_links (created_at DESC);
CREATE INDEX IF NOT EXISTS ad_links_kind_idx ON ad_links (kind, created_at DESC);

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
    SELECT DISTINCT telegram_id FROM pay_orders WHERE status = 'granted'
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
DROP INDEX IF EXISTS users_idle_nudge_idx;
CREATE INDEX IF NOT EXISTS users_idle_nudge_idx
    ON users (idle_nudge_step)
    WHERE blocked_at IS NULL AND idle_nudge_step < 45;
ALTER TABLE users ADD COLUMN IF NOT EXISTS nodevice_nudge_step INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS nodevice_nudge_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS unpaid_nudge_step INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS unpaid_nudge_at TIMESTAMPTZ;

DROP TABLE IF EXISTS auto_topups;

ALTER TABLE users ADD COLUMN IF NOT EXISTS router_expire_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS billing_paused_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS devices_one_router_uidx
    ON devices (telegram_id)
    WHERE kind = 'router';

CREATE TABLE IF NOT EXISTS cabinet_login_challenges (
    id TEXT PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
    ip_hash TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    session_token TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS cabinet_login_challenges_tg_idx
    ON cabinet_login_challenges (telegram_id, created_at DESC);
CREATE INDEX IF NOT EXISTS cabinet_login_challenges_exp_idx
    ON cabinet_login_challenges (expires_at);
-- «Войти через Telegram»: the browser asks first, the account is known only after /start in the bot.
ALTER TABLE cabinet_login_challenges ALTER COLUMN telegram_id DROP NOT NULL;
ALTER TABLE cabinet_login_challenges ADD COLUMN IF NOT EXISTS device TEXT NOT NULL DEFAULT '';
ALTER TABLE cabinet_tokens ADD COLUMN IF NOT EXISTS device TEXT NOT NULL DEFAULT '';




ALTER TABLE users ADD COLUMN IF NOT EXISTS legal_notice_at TIMESTAMPTZ;

ALTER TABLE users ADD COLUMN IF NOT EXISTS bot_started_at TIMESTAMPTZ;
-- Only the /start handler claims this welcome marker; Web App registration does not.
UPDATE users SET bot_started_at = welcome_intro_sent_at
WHERE bot_started_at IS NULL AND welcome_intro_sent_at IS NOT NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS checkout_token TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS checkout_started_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS checkout_payment_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS checkout_nudge_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS payment_nudge_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS users_checkout_nudge_idx ON users (checkout_started_at)
WHERE checkout_started_at IS NOT NULL AND checkout_nudge_at IS NULL;
INSERT INTO app_flags (key, value) VALUES ('payment_nudge', '1') ON CONFLICT (key) DO NOTHING;

ALTER TABLE users ADD COLUMN IF NOT EXISTS gift_claimed_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS checkout_url TEXT;

ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_fraction INTEGER NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS referral_payment_rewards (
    payment_key TEXT PRIMARY KEY,
    invitee_id BIGINT NOT NULL,
    referrer_id BIGINT,
    topup_rub INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL,
    reward_rub INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Retain checkout entry after a successful payment clears the active invoice.
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_checkout_at TIMESTAMPTZ;
UPDATE users u SET first_checkout_at = h.started
FROM (
    SELECT telegram_id, MIN(created_at) AS started FROM (
        SELECT telegram_id, created_at FROM pay_orders
        UNION ALL SELECT telegram_id, created_at FROM payments
        UNION ALL SELECT telegram_id, checkout_started_at AS created_at FROM users WHERE checkout_started_at IS NOT NULL
    ) history GROUP BY telegram_id
) h WHERE h.telegram_id=u.telegram_id AND u.first_checkout_at IS NULL;

-- Retain the device milestone after the device is deleted. Connected users had a device by then.
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_device_at TIMESTAMPTZ;
UPDATE users u SET first_device_at = h.added
FROM (
    SELECT x.telegram_id, LEAST(
        (SELECT MIN(d.created_at) FROM devices d WHERE d.telegram_id = x.telegram_id),
        x.first_online_at) AS added
    FROM users x WHERE x.first_device_at IS NULL
) h WHERE h.telegram_id=u.telegram_id AND h.added IS NOT NULL AND u.first_device_at IS NULL;


CREATE TABLE IF NOT EXISTS device_exit_feedback (
    token TEXT PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason TEXT CHECK (reason IN ('expensive','not_working','not_needed','other')),
    answered_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS device_exit_feedback_created_idx ON device_exit_feedback(created_at DESC);

ALTER TABLE device_exit_feedback ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS device_exit_feedback_user_idx ON device_exit_feedback(telegram_id, created_at DESC);


ALTER TABLE pay_orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;
ALTER TABLE pay_orders ADD COLUMN IF NOT EXISTS method TEXT;
ALTER TABLE pay_orders ADD COLUMN IF NOT EXISTS fail_notice_at TIMESTAMPTZ;
ALTER TABLE pay_orders ADD COLUMN IF NOT EXISTS checked_at TIMESTAMPTZ;
-- What the invoice asked for, in kopecks: a paid notice for less is not credited.
ALTER TABLE pay_orders ADD COLUMN IF NOT EXISTS amount_kop BIGINT;
CREATE TABLE IF NOT EXISTS reminder_deliveries (
    token TEXT PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','failed')),
    message_id BIGINT,
    sent_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    connected_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS reminder_deliveries_user_click_idx ON reminder_deliveries(telegram_id,clicked_at DESC);
CREATE INDEX IF NOT EXISTS reminder_deliveries_created_idx ON reminder_deliveries(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS reminder_deliveries_message_idx ON reminder_deliveries(telegram_id,message_id) WHERE message_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS reminder_clicks (
    id BIGSERIAL PRIMARY KEY,
    token TEXT NOT NULL REFERENCES reminder_deliveries(token) ON DELETE CASCADE,
    clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS reminder_clicks_token_idx ON reminder_clicks(token,clicked_at DESC);

-- Independent, manually launched three-friend promotion.
CREATE TABLE IF NOT EXISTS referral_campaigns (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    stopped_at TIMESTAMPTZ,
    reward_rub INTEGER NOT NULL CHECK (reward_rub > 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS referral_campaign_one_active
    ON referral_campaigns ((1)) WHERE stopped_at IS NULL;
CREATE TABLE IF NOT EXISTS referral_campaign_friends (
    invitee_id BIGINT PRIMARY KEY REFERENCES users(telegram_id),
    campaign_id BIGINT NOT NULL REFERENCES referral_campaigns(id),
    referrer_id BIGINT NOT NULL REFERENCES users(telegram_id),
    payment_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS referral_campaign_friends_progress
    ON referral_campaign_friends (campaign_id, referrer_id);
CREATE TABLE IF NOT EXISTS referral_campaign_awards (
    campaign_id BIGINT NOT NULL REFERENCES referral_campaigns(id),
    referrer_id BIGINT NOT NULL REFERENCES users(telegram_id),
    amount INTEGER NOT NULL CHECK (amount > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (campaign_id, referrer_id)
);

CREATE TABLE IF NOT EXISTS referral_campaign_messages (
    campaign_id BIGINT NOT NULL REFERENCES referral_campaigns(id),
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    retry_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    error TEXT,
    PRIMARY KEY (campaign_id, telegram_id)
);
CREATE INDEX IF NOT EXISTS referral_campaign_messages_queue
    ON referral_campaign_messages (retry_at) WHERE status IN ('pending','sending');

CREATE TABLE IF NOT EXISTS referral_campaign_schedule (
    id INTEGER PRIMARY KEY CHECK (id=1),
    scheduled_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE referral_campaign_messages ADD COLUMN IF NOT EXISTS retryable BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_support_pending BOOLEAN NOT NULL DEFAULT FALSE;

-- Each manual broadcast is a durable run, separate from message templates.
CREATE TABLE IF NOT EXISTS broadcast_runs (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    template TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    total INTEGER NOT NULL DEFAULT 0,
    sent INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
ALTER TABLE reminder_deliveries ADD COLUMN IF NOT EXISTS broadcast_id BIGINT REFERENCES broadcast_runs(id);
CREATE INDEX IF NOT EXISTS reminder_deliveries_broadcast_idx ON reminder_deliveries(broadcast_id) WHERE broadcast_id IS NOT NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS vpn_feedback TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS vpn_feedback_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS idle_snoozed_at TIMESTAMPTZ;
CREATE TABLE IF NOT EXISTS onboarding_events (
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(telegram_id,stage)
);
CREATE TABLE IF NOT EXISTS onboarding_tracking_epoch (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO onboarding_tracking_epoch(singleton) VALUES(TRUE) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS pending_legal_messages (
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    message_id BIGINT NOT NULL,
    body TEXT NOT NULL,
    markup TEXT,
    PRIMARY KEY (telegram_id, message_id)
);

ALTER TABLE tickets ADD COLUMN IF NOT EXISTS support_rating SMALLINT CHECK (support_rating BETWEEN 1 AND 5);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS rated_at TIMESTAMPTZ;
-- When support last opened the dialog: the client sees «прочитано» on messages before it.
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS admin_seen_at TIMESTAMPTZ;

ALTER TABLE users ADD COLUMN IF NOT EXISTS quiet_notifications BOOLEAN NOT NULL DEFAULT FALSE;

-- Durable payment receipts: credit and receipt commit together; side effects can retry.
CREATE TABLE IF NOT EXISTS payment_receipts (
    payment_key TEXT PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    plan_code TEXT NOT NULL,
    amount INTEGER NOT NULL,
    router_days INTEGER NOT NULL DEFAULT 0,
    first_payment BOOLEAN NOT NULL,
    referral_enabled BOOLEAN NOT NULL,
    invitee_bonus INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effects_done_at TIMESTAMPTZ,
    retry_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS payment_receipts_pending_idx ON payment_receipts(retry_at)
    WHERE effects_done_at IS NULL;

-- Reservations serialize optional messages from all workers, including multiple processes.
CREATE TABLE IF NOT EXISTS optional_message_slots (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS optional_message_slots_user_idx ON optional_message_slots(telegram_id, created_at);

ALTER TABLE broadcast_runs ADD COLUMN IF NOT EXISTS skipped INTEGER NOT NULL DEFAULT 0;
-- What was asked for: audience, test share (sample, %), parent run for «отправить остальным», media.
ALTER TABLE broadcast_runs ADD COLUMN IF NOT EXISTS spec JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_exhausted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS winback_last_sent_at TIMESTAMPTZ;

-- Track actual crossings, not the date of the last notification.
CREATE OR REPLACE FUNCTION track_balance_exhaustion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.balance_rub > 0 THEN
        NEW.balance_exhausted_at := NULL;
    ELSIF OLD.balance_rub > 0 AND NEW.balance_rub <= 0 THEN
        NEW.balance_exhausted_at := NOW();
    END IF;
    RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS users_balance_exhaustion ON users;
CREATE TRIGGER users_balance_exhaustion BEFORE UPDATE OF balance_rub ON users
    FOR EACH ROW EXECUTE FUNCTION track_balance_exhaustion();

ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS recipient_telegram_id BIGINT;

CREATE TABLE IF NOT EXISTS winback_offers (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    promo_id BIGINT NOT NULL UNIQUE REFERENCES promo_codes(id),
    device_count INTEGER NOT NULL CHECK(device_count > 0),
    gift_rub INTEGER NOT NULL CHECK(gift_rub > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','sending','sent','cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    retry_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attempts INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS winback_offers_pending_user ON winback_offers(telegram_id)
    WHERE status IN ('pending','sending');
INSERT INTO app_flags(key,value) VALUES ('winback_promo','1') ON CONFLICT DO NOTHING;
CREATE INDEX IF NOT EXISTS users_exhausted_balance_idx ON users(balance_exhausted_at,telegram_id)
    WHERE balance_rub <= 0;

-- Durable results of personal return offers, independent of device removal.
ALTER TABLE winback_offers ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ;
ALTER TABLE winback_offers ADD COLUMN IF NOT EXISTS debt_repaid_rub INTEGER;
ALTER TABLE winback_offers ADD COLUMN IF NOT EXISTS connected_at TIMESTAMPTZ;
UPDATE winback_offers w SET activated_at=u.created_at FROM promo_codes p,promo_uses u
WHERE w.promo_id=p.id AND u.code=p.code AND u.telegram_id=w.telegram_id AND w.activated_at IS NULL;
CREATE OR REPLACE FUNCTION track_winback_connection() RETURNS trigger AS $$
BEGIN
    UPDATE winback_offers SET connected_at=NEW.last_online_at
    WHERE telegram_id=NEW.telegram_id AND activated_at IS NOT NULL AND connected_at IS NULL
      AND NEW.last_online_at>=activated_at AND NEW.last_online_at<activated_at+INTERVAL '7 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS winback_connection ON devices;
CREATE TRIGGER winback_connection AFTER INSERT OR UPDATE OF last_online_at ON devices
FOR EACH ROW EXECUTE FUNCTION track_winback_connection();
UPDATE winback_offers w SET connected_at=(SELECT MIN(d.last_online_at) FROM devices d
WHERE d.telegram_id=w.telegram_id AND d.last_online_at>=w.activated_at
AND d.last_online_at<w.activated_at+INTERVAL '7 days')
WHERE w.activated_at IS NOT NULL AND w.connected_at IS NULL;
CREATE INDEX IF NOT EXISTS winback_offers_sent_idx ON winback_offers(sent_at);
CREATE INDEX IF NOT EXISTS payment_receipts_user_date_idx ON payment_receipts(telegram_id,created_at);
CREATE INDEX IF NOT EXISTS winback_offers_connection_idx ON winback_offers(telegram_id,activated_at)
WHERE activated_at IS NOT NULL AND connected_at IS NULL;

-- Only new receipts enter this outbox; do not resend historical payments on deploy.
ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS notice_status TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS notice_retry_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS notice_sent_at TIMESTAMPTZ;
ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS first_bonus_rub INT NOT NULL DEFAULT 0;
-- «Возвращайтесь с бонусом» (app/return_bonus.py): added on top of a top-up after the offer.
ALTER TABLE payment_receipts ADD COLUMN IF NOT EXISTS return_bonus_rub INT NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS payment_receipts_notice_pending ON payment_receipts(notice_retry_at)
WHERE notice_status='pending';

CREATE TABLE IF NOT EXISTS funnel_graphs (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    graph JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS funnel_step_sends (
    telegram_id BIGINT NOT NULL,
    step_id TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (telegram_id, step_id)
);

-- Gift credit stays intact until the first confirmed VPN connection.
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_waiting_connection BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS legacy_last_online_at TIMESTAMPTZ;
-- The customer's own label for a device in the cabinet: an emoji from DEVICE_ICONS (app/web.py), empty = by platform.
ALTER TABLE devices ADD COLUMN IF NOT EXISTS icon TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS legacy_first_online_at TIMESTAMPTZ;
-- Remove unverifiable legacy online values once; panel sync restores real connection dates.
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM app_flags WHERE key='online_evidence_v2') THEN
  UPDATE devices SET legacy_last_online_at=last_online_at,last_online_at=NULL;
  UPDATE users u SET legacy_first_online_at=first_online_at,first_online_at=NULL
   WHERE COALESCE(u.used_traffic_bytes,0)=0 AND COALESCE(u.lifetime_traffic_bytes,0)=0
    AND NOT EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id
      AND (COALESCE(d.used_traffic_bytes,0)>0 OR COALESCE(d.lifetime_traffic_bytes,0)>0));
  UPDATE users SET trial_waiting_connection=TRUE
   WHERE trial_used AND first_online_at IS NULL AND NOT COALESCE(has_paid_topup,FALSE) AND balance_rub > 0;
  INSERT INTO app_flags(key,value) VALUES('online_evidence_v2','1');
 END IF;
END $$;

ALTER TABLE reminder_deliveries ADD COLUMN IF NOT EXISTS cabinet_opened_at TIMESTAMPTZ;
ALTER TABLE reminder_deliveries ADD COLUMN IF NOT EXISTS device_added_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS checkout_feedback (
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    checkout_token TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('broken','price','payment','later')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (telegram_id, checkout_token)
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS marketing_pause_until TIMESTAMPTZ;

-- «Застрял на подключении» alert to the admin (app/stuck_alert.py): sent once per person.
ALTER TABLE users ADD COLUMN IF NOT EXISTS stuck_alert_at TIMESTAMPTZ;

-- A/B test «подарок сразу на балансе» (app/auto_gift.py): one row per test, one group per new person.
CREATE TABLE IF NOT EXISTS auto_gift_tests (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS auto_gift_arms (
    telegram_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    test_id BIGINT NOT NULL REFERENCES auto_gift_tests(id) ON DELETE CASCADE,
    arm TEXT NOT NULL CHECK (arm IN ('auto','manual')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS auto_gift_arms_test_idx ON auto_gift_arms(test_id, arm);

-- The «почему не продолжили» question was dropped the day it shipped.
DROP TABLE IF EXISTS gift_end_feedback;
ALTER TABLE users ADD COLUMN IF NOT EXISTS marketing_pause_started_at TIMESTAMPTZ;

-- Invitation card interactions; clicks are not confirmed shares.
CREATE TABLE IF NOT EXISTS invitation_card_events (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK(action IN ('share','copy')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS invitation_card_events_created_idx ON invitation_card_events(created_at);

-- Daily activity aggregation and durable digest delivery marker.
CREATE TABLE IF NOT EXISTS admin_activity_daily (
    day DATE NOT NULL,
    telegram_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    source TEXT NOT NULL,
    events INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (day, telegram_id, action, source)
);
CREATE TABLE IF NOT EXISTS admin_activity_digests (
    day DATE PRIMARY KEY,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- First observed invitation intent; Telegram does not confirm actual sharing.
ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_opened_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by) WHERE referred_by IS NOT NULL;

-- Advertisers open their own stats page by a secret token and can add (not delete) ad links.
CREATE TABLE IF NOT EXISTS ad_partners (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    revoked_at TIMESTAMPTZ
);
ALTER TABLE ad_links ADD COLUMN IF NOT EXISTS partner_id BIGINT REFERENCES ad_partners (id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ad_links_partner_idx ON ad_links (partner_id) WHERE partner_id IS NOT NULL;
-- What the placement cost, entered by hand: the admin shows the price of one payer and the payback.
ALTER TABLE ad_links ADD COLUMN IF NOT EXISTS spend_rub INTEGER CHECK (spend_rub IS NULL OR spend_rub >= 0);
-- Referral bonus for reaching the main menu. Existing rows get the epoch so
-- old invitees are not paid retroactively; new rows start as NULL.
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_menu_bonus_at TIMESTAMPTZ DEFAULT 'epoch';
ALTER TABLE users ALTER COLUMN referral_menu_bonus_at SET DEFAULT NULL;
-- Inviter's bonus once the invited friend first connects VPN. Existing rows get the epoch:
-- under the old rule the inviter was already paid when the friend reached the menu.
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_connect_bonus_at TIMESTAMPTZ DEFAULT 'epoch';
ALTER TABLE users ALTER COLUMN referral_connect_bonus_at SET DEFAULT NULL;
-- Gift days offered inside funnel messages: one tap credits N days for the user's devices.
CREATE TABLE IF NOT EXISTS funnel_gifts (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    step_id TEXT NOT NULL,
    days INTEGER NOT NULL CHECK (days > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    claimed_at TIMESTAMPTZ,
    gift_rub INTEGER,
    debt_repaid_rub INTEGER
);
CREATE INDEX IF NOT EXISTS funnel_gifts_user_idx ON funnel_gifts (telegram_id, created_at DESC);
-- Which funnel step a tracked message belongs to, for click statistics.
ALTER TABLE reminder_deliveries ADD COLUMN IF NOT EXISTS step_id TEXT;
CREATE INDEX IF NOT EXISTS reminder_deliveries_step_idx ON reminder_deliveries (step_id, created_at)
    WHERE step_id IS NOT NULL;

-- Payments in TON through the chat widget. order_id is also the transfer comment.
CREATE TABLE IF NOT EXISTS ton_orders (
    order_id TEXT PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    rub INTEGER NOT NULL,
    nano BIGINT NOT NULL,
    rate_rub NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    chat_id BIGINT,
    message_id BIGINT,
    sent_at TIMESTAMPTZ,
    sender TEXT,
    msg_hash TEXT,
    tx_hash TEXT UNIQUE,
    paid_nano BIGINT,
    credited_rub INTEGER,
    paid_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ton_orders_open_idx ON ton_orders (created_at) WHERE status IN ('pending', 'sent');
CREATE INDEX IF NOT EXISTS ton_orders_user_idx ON ton_orders (telegram_id, created_at DESC);

-- Every incoming transfer seen on the shop wallet; order_id is NULL for transfers nobody could match.
-- Gifts a user shows on the Telegram profile and the wealth rating from them, cached for the admin card.
CREATE TABLE IF NOT EXISTS user_gifts (
    telegram_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 0,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Total device traffic at the start of each Moscow day: today's traffic is the growth since then.
CREATE TABLE IF NOT EXISTS traffic_days (
    day DATE PRIMARY KEY,
    start_bytes BIGINT NOT NULL,
    taken_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ton_incoming (
    tx_hash TEXT PRIMARY KEY,
    sender TEXT,
    nano BIGINT NOT NULL,
    comment TEXT,
    order_id TEXT,
    utime TIMESTAMPTZ,
    seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Receipt keys of the previous provider («<old>:<order>») become «order:<order>»; does nothing once done.
DO $$
DECLARE old_prefix TEXT := 'rollypay:';
BEGIN
    UPDATE payment_receipts SET payment_key = 'order:' || substr(payment_key, length(old_prefix) + 1)
        WHERE payment_key LIKE old_prefix || '%';
    UPDATE referral_payment_rewards SET payment_key = 'order:' || substr(payment_key, length(old_prefix) + 1)
        WHERE payment_key LIKE old_prefix || '%';
    UPDATE referral_campaign_friends SET payment_key = 'order:' || substr(payment_key, length(old_prefix) + 1)
        WHERE payment_key LIKE old_prefix || '%';
END $$;

-- Who opened a member's invite link; attached = the visitor became that member's friend. A visitor who already
-- used the bot (or came by someone else's link) stays unattached: it is an invite attempt, not a friend.
CREATE TABLE IF NOT EXISTS referral_link_visits (
    referrer_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    visitor_id BIGINT NOT NULL,
    attached BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (referrer_id, visitor_id)
);
CREATE INDEX IF NOT EXISTS invitation_card_events_user_idx ON invitation_card_events(telegram_id);

-- How a user first reached the bot: start (/start, payload = its parameter, '' for none), app (Mini App,
-- payload = start_param), support, report or other. NULL for users who came before this was recorded.
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_entry_via TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_start_payload TEXT;
-- Early «баланс заканчивается» (three days ahead) for people who paid before; the one-day warning stays in trial_end_nudge_at.
ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_warn3_at TIMESTAMPTZ;

-- Any balance increase (payment, referral bonus, promo, admin credit, refund) wakes the app at once:
-- app/balance_watch.py listens and turns back on devices that were switched off for lack of money.
CREATE OR REPLACE FUNCTION notify_balance_up() RETURNS trigger AS $$
BEGIN
    IF COALESCE(NEW.balance_rub, 0) > COALESCE(OLD.balance_rub, 0) THEN
        PERFORM pg_notify('balance_up', NEW.telegram_id::text);
    END IF;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS users_balance_up ON users;
CREATE TRIGGER users_balance_up AFTER UPDATE OF balance_rub ON users
    FOR EACH ROW EXECUTE FUNCTION notify_balance_up();

-- «Подарить другу»: the giver pays from their balance (only money they topped up themselves), the friend opens
-- the gift by its code and the amount lands on their balance. Until opened, the giver can take it back.
CREATE TABLE IF NOT EXISTS friend_gifts (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    from_telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    amount_rub INTEGER NOT NULL CHECK (amount_rub > 0),
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    claimed_by BIGINT,
    claimed_at TIMESTAMPTZ,
    returned_at TIMESTAMPTZ,
    thanked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS friend_gifts_from_idx ON friend_gifts (from_telegram_id, created_at DESC);
CREATE INDEX IF NOT EXISTS friend_gifts_claimed_idx ON friend_gifts (claimed_by) WHERE claimed_by IS NOT NULL;
-- Admins gift any amount to anyone; their gifts are not paid from their balance.
ALTER TABLE friend_gifts ADD COLUMN IF NOT EXISTS from_admin BOOLEAN NOT NULL DEFAULT FALSE;
-- A giveaway: `count` equal gifts behind one link, first come, one each; claims say who took one.
ALTER TABLE friend_gifts ADD COLUMN IF NOT EXISTS count INTEGER NOT NULL DEFAULT 1;
ALTER TABLE friend_gifts ADD COLUMN IF NOT EXISTS claimed_count INTEGER NOT NULL DEFAULT 0;
-- How the gift looks (chosen by the giver): violet, festive, gold or sunset.
ALTER TABLE friend_gifts ADD COLUMN IF NOT EXISTS style TEXT NOT NULL DEFAULT 'violet';
ALTER TABLE friend_gifts ADD COLUMN IF NOT EXISTS greeting TEXT NOT NULL DEFAULT '';
CREATE TABLE IF NOT EXISTS friend_gift_claims (
    gift_id BIGINT NOT NULL REFERENCES friend_gifts(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL,
    amount_rub INTEGER NOT NULL,
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    thanked_at TIMESTAMPTZ,
    PRIMARY KEY (gift_id, telegram_id)
);
-- Single gifts opened before claims existed.
INSERT INTO friend_gift_claims (gift_id, telegram_id, amount_rub, claimed_at, thanked_at)
    SELECT id, claimed_by, amount_rub, COALESCE(claimed_at, NOW()), thanked_at FROM friend_gifts
    WHERE claimed_by IS NOT NULL ON CONFLICT DO NOTHING;
UPDATE friend_gifts SET claimed_count=1 WHERE claimed_by IS NOT NULL AND claimed_count=0;

-- A/B tests of the bot's automatic messages (app/experiments.py): one running test per step.
CREATE TABLE IF NOT EXISTS funnel_experiments (
    id BIGSERIAL PRIMARY KEY,
    step_id TEXT NOT NULL,
    holdout_pct INTEGER NOT NULL DEFAULT 0 CHECK (holdout_pct BETWEEN 0 AND 50),
    b_pct INTEGER NOT NULL DEFAULT 0 CHECK (b_pct BETWEEN 0 AND 100),
    b_text TEXT,
    b_gift_days INTEGER CHECK (b_gift_days IS NULL OR b_gift_days BETWEEN 1 AND 14),
    note TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS funnel_experiments_running_idx ON funnel_experiments(step_id) WHERE stopped_at IS NULL;
-- «Возвращайтесь с бонусом»: arm B gets this percent instead of the one in the settings (app/return_bonus.py).
ALTER TABLE funnel_experiments ADD COLUMN IF NOT EXISTS b_bonus_pct INTEGER CHECK (b_bonus_pct IS NULL OR b_bonus_pct BETWEEN 1 AND 100);
-- Who was due the step while the test ran and which arm they got. Control is never sent the step.
CREATE TABLE IF NOT EXISTS funnel_experiment_users (
    experiment_id BIGINT NOT NULL REFERENCES funnel_experiments(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    arm TEXT NOT NULL CHECK (arm IN ('a','b','control')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    PRIMARY KEY (experiment_id, telegram_id)
);
CREATE INDEX IF NOT EXISTS funnel_experiment_users_user_idx ON funnel_experiment_users(telegram_id);
-- A/B test of a manual broadcast: who got A, B or nothing (control). See app/experiments.py.
CREATE TABLE IF NOT EXISTS broadcast_arms (
    run_id BIGINT NOT NULL REFERENCES broadcast_runs(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    arm TEXT NOT NULL CHECK (arm IN ('a','b','control')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    PRIMARY KEY (run_id, telegram_id)
);

-- Admin-granted right to gift any amount without paying from the balance, like an admin.
ALTER TABLE users ADD COLUMN IF NOT EXISTS gift_unlimited BOOLEAN NOT NULL DEFAULT FALSE;

-- The Telegram account was deleted ("user is deactivated"): nothing reaches it, the admin cleans such profiles up.
ALTER TABLE users ADD COLUMN IF NOT EXISTS tg_deleted_at TIMESTAMPTZ;
UPDATE users u
SET tg_deleted_at = m.first_at, bot_blocked_at = COALESCE(u.bot_blocked_at, m.first_at)
FROM (
    SELECT telegram_id, MIN(created_at) AS first_at
    FROM message_log
    WHERE status = 'failed'
      AND telegram_id IS NOT NULL
      AND (
        extra->>'error' = 'аккаунт Telegram удалён'
        OR COALESCE(extra->>'error_raw', '') ILIKE '%deactivated%'
      )
    GROUP BY telegram_id
) m
WHERE u.telegram_id = m.telegram_id
  AND u.tg_deleted_at IS NULL;

-- NFT gifts for real friends (app/friend_nft.py).
-- Days a person had VPN online: a friend counts after using it 3 days out of the first 7.
CREATE TABLE IF NOT EXISTS online_days (
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    day DATE NOT NULL,
    PRIMARY KEY (telegram_id, day)
);
CREATE OR REPLACE FUNCTION track_online_day() RETURNS trigger AS $$
BEGIN
    IF NEW.last_online_at IS NOT NULL AND (TG_OP = 'INSERT' OR NEW.last_online_at IS DISTINCT FROM OLD.last_online_at) THEN
        INSERT INTO online_days(telegram_id, day) VALUES (NEW.telegram_id, (NEW.last_online_at AT TIME ZONE 'UTC')::date)
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS online_day ON devices;
CREATE TRIGGER online_day AFTER INSERT OR UPDATE OF last_online_at ON devices
FOR EACH ROW EXECUTE FUNCTION track_online_day();
-- A friend who paid by the invite link: on check for a week, then counted (ok) or not (bad, with the reason).
CREATE TABLE IF NOT EXISTS friend_nft_checks (
    invitee_id BIGINT PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    referrer_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    paid_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'check' CHECK (status IN ('check','ok','bad')),
    reason TEXT,
    by_admin BOOLEAN NOT NULL DEFAULT FALSE,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS friend_nft_checks_referrer_idx ON friend_nft_checks(referrer_id);
CREATE INDEX IF NOT EXISTS friend_nft_checks_open_idx ON friend_nft_checks(paid_at) WHERE status = 'check';
-- An earned gift: waits for the admin to transfer it by hand, then given (with the NFT link) or cancelled.
CREATE TABLE IF NOT EXISTS friend_nft_rewards (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    need INTEGER NOT NULL,
    gift JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'wait' CHECK (status IN ('wait','given','cancelled')),
    nft_link TEXT,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    given_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS friend_nft_rewards_step ON friend_nft_rewards(telegram_id, need) WHERE status <> 'cancelled';
CREATE INDEX IF NOT EXISTS friend_nft_rewards_wait_idx ON friend_nft_rewards(created_at) WHERE status = 'wait';

-- «Шеринг подписки»: the IPs each device was seen from (Remnawave /connections/by-node), kept 30 days.
CREATE TABLE IF NOT EXISTS device_ips (
    device_id BIGINT NOT NULL REFERENCES devices (id) ON DELETE CASCADE,
    ip TEXT NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (device_id, ip)
);
CREATE INDEX IF NOT EXISTS device_ips_last_seen_idx ON device_ips (last_seen);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS sharing_alert_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS sharing_alert_ips INTEGER;

-- «Подключился, но трафика нет» (app/stuck_alert.py): when a device first went online, and when the admin heard of it.
ALTER TABLE devices ADD COLUMN IF NOT EXISTS first_online_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS no_traffic_alert_at TIMESTAMPTZ;
CREATE OR REPLACE FUNCTION track_device_first_online() RETURNS trigger AS $$
BEGIN
    IF NEW.first_online_at IS NULL AND NEW.last_online_at IS NOT NULL THEN
        NEW.first_online_at := NEW.last_online_at;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS device_first_online ON devices;
CREATE TRIGGER device_first_online BEFORE INSERT OR UPDATE OF last_online_at ON devices
FOR EACH ROW EXECUTE FUNCTION track_device_first_online();
UPDATE devices SET first_online_at = last_online_at WHERE first_online_at IS NULL AND last_online_at IS NOT NULL;

-- «Спящие» (app/sleepers.py): never online, never paid, the bot's messages are over. sleep_at: said «Пока не нужен».
ALTER TABLE users ADD COLUMN IF NOT EXISTS sleep_at TIMESTAMPTZ;
-- Answers to «Что помешало?»: the last answer per person.
CREATE TABLE IF NOT EXISTS why_answers (
    telegram_id BIGINT PRIMARY KEY REFERENCES users (telegram_id) ON DELETE CASCADE,
    answer TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Exact blocks of the bot (Telegram's my_chat_member «kicked» in a private chat), with what the person had
-- reached and the last message the bot had sent: «Когда блокируют» in the statistics.
CREATE TABLE IF NOT EXISTS bot_blocks (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    blocked_at TIMESTAMPTZ NOT NULL,
    unblocked_at TIMESTAMPTZ,
    stage TEXT NOT NULL,
    since_start_sec BIGINT,
    last_kind TEXT,
    last_title TEXT,
    last_sent_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS bot_blocks_at_idx ON bot_blocks (blocked_at DESC);
CREATE INDEX IF NOT EXISTS bot_blocks_tg_idx ON bot_blocks (telegram_id, blocked_at DESC);

-- A/B test of the cabinet's «install the app» step (app/install_test.py): one group per person per test.
CREATE TABLE IF NOT EXISTS install_tests (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS install_arms (
    test_id BIGINT NOT NULL REFERENCES install_tests(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    arm TEXT NOT NULL CHECK (arm IN ('old','new')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (test_id, telegram_id)
);
CREATE INDEX IF NOT EXISTS install_arms_test_idx ON install_arms(test_id, arm);

-- «Шеринг»: caught sharing a key. Stays after unblocking, as a mark. sharing_penalty_rub is what was taken
-- to bring the balance to −100 000 ₽, so «Разблокировать» can give exactly that back.
ALTER TABLE users ADD COLUMN IF NOT EXISTS sharing_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sharing_penalty_rub INTEGER;

-- Telegram Ads (app/tg_ads.py): one row per ad of the account, tied to an ad link by the start=ad_<slug> of its URL.
CREATE TABLE IF NOT EXISTS tg_ads (
    ad_id BIGINT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    promote_url TEXT NOT NULL DEFAULT '',
    slug TEXT,
    ad_link_id BIGINT REFERENCES ad_links (id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL DEFAULT 'TON',
    cpm NUMERIC NOT NULL DEFAULT 0,
    spent NUMERIC NOT NULL DEFAULT 0,
    spent_rub INTEGER,
    views INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    actions INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS tg_ads_link_idx ON tg_ads (ad_link_id) WHERE ad_link_id IS NOT NULL;

-- Автопополнение (app/autopay.py): one CISPay subscription per person. Each charge is a pay_orders row «ap-<tx>».
CREATE TABLE IF NOT EXISTS autopay (
    telegram_id BIGINT PRIMARY KEY REFERENCES users (telegram_id),
    subscription_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'none',
    amount_rub INTEGER NOT NULL DEFAULT 0,
    interval_days INTEGER NOT NULL DEFAULT 0,
    pay_url TEXT,
    next_charge_at TIMESTAMPTZ,
    last_charge_at TIMESTAMPTZ,
    ended_reason TEXT,
    reminded_for TIMESTAMPTZ,
    failed_tx TEXT,
    declined_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE autopay ADD COLUMN IF NOT EXISTS fails INTEGER NOT NULL DEFAULT 0;
ALTER TABLE autopay ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ;

-- A/B test of the living frog on the cabinet's home card (app/frog_test.py): one group per person per test,
-- and per day how often they opened the cabinet, played with the frog and pressed «Пополнить» there.
CREATE TABLE IF NOT EXISTS frog_tests (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS frog_arms (
    test_id BIGINT NOT NULL REFERENCES frog_tests(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    arm TEXT NOT NULL CHECK (arm IN ('frog','plain')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (test_id, telegram_id)
);
CREATE INDEX IF NOT EXISTS frog_arms_test_idx ON frog_arms(test_id, arm);
CREATE TABLE IF NOT EXISTS frog_days (
    test_id BIGINT NOT NULL REFERENCES frog_tests(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    day DATE NOT NULL,
    opens INTEGER NOT NULL DEFAULT 0,
    plays INTEGER NOT NULL DEFAULT 0,
    topups INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (test_id, telegram_id, day)
);

-- «Затраты» in the admin (app/expenses.py): the service's own regular bills — hosting, domains, servers.
-- next_date is the next payment; «Оплачено» logs it in service_expense_payments and moves the date one period on.
CREATE TABLE IF NOT EXISTS service_expenses (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    currency TEXT NOT NULL DEFAULT 'RUB',
    period TEXT NOT NULL DEFAULT 'month' CHECK (period IN ('month','quarter','year','once')),
    next_date DATE NOT NULL,
    anchor_day SMALLINT,
    url TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    last_paid_at TIMESTAMPTZ,
    done_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS service_expense_payments (
    id BIGSERIAL PRIMARY KEY,
    expense_id BIGINT REFERENCES service_expenses(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'RUB',
    due_date DATE,
    paid_on DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS service_expense_payments_paid_idx ON service_expense_payments(paid_on);
-- One row per reminder sent to the channel: (bill, payment date, days before; -1 = overdue) never goes twice.
CREATE TABLE IF NOT EXISTS expense_reminders (
    expense_id BIGINT NOT NULL REFERENCES service_expenses(id) ON DELETE CASCADE,
    due_date DATE NOT NULL,
    stage SMALLINT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (expense_id, due_date, stage)
);

-- Кейсы с лягушкой (app/frog_cases.py): cases waiting, the frog on the home card and a gift to show once.
CREATE TABLE IF NOT EXISTS frog_case_users (
    telegram_id BIGINT PRIMARY KEY,
    cases_left INTEGER NOT NULL DEFAULT 0 CHECK (cases_left >= 0),
    skin SMALLINT,
    gift_count INTEGER NOT NULL DEFAULT 0,
    gift_note TEXT NOT NULL DEFAULT '',
    gift_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- the frogs a person has, and how many times each dropped
CREATE TABLE IF NOT EXISTS frog_case_skins (
    telegram_id BIGINT NOT NULL,
    skin SMALLINT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    first_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (telegram_id, skin)
);
-- every case given (topup / subscription / admin) and opened (open); ref keeps a payment from giving twice
CREATE TABLE IF NOT EXISTS frog_case_log (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    kind TEXT NOT NULL,
    delta INTEGER NOT NULL,
    skin SMALLINT,
    ref TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS frog_case_log_user ON frog_case_log (telegram_id, id DESC);
CREATE UNIQUE INDEX IF NOT EXISTS frog_case_log_ref ON frog_case_log (kind, ref) WHERE ref <> '';

-- A/B test of the first message after /start (app/welcome_test.py): sticker and text, or one card with a banner.
CREATE TABLE IF NOT EXISTS welcome_tests (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS welcome_arms (
    test_id BIGINT NOT NULL REFERENCES welcome_tests(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    arm TEXT NOT NULL CHECK (arm IN ('plain','card')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (test_id, telegram_id)
);
CREATE INDEX IF NOT EXISTS welcome_arms_test_idx ON welcome_arms(test_id, arm);

-- Xray logs from the nodes for watched devices (app/node_logs.py, deploy/node-logs/ship.py); kept 72 hours.
CREATE TABLE IF NOT EXISTS node_log_lines (
    id BIGSERIAL PRIMARY KEY,
    node TEXT NOT NULL,
    at TIMESTAMPTZ NOT NULL,
    ip TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    device_id BIGINT,
    telegram_id BIGINT,
    kind TEXT NOT NULL,
    dest TEXT NOT NULL DEFAULT '',
    raw TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS node_log_lines_device ON node_log_lines (device_id, at DESC);
CREATE INDEX IF NOT EXISTS node_log_lines_user ON node_log_lines (telegram_id, at DESC);
CREATE INDEX IF NOT EXISTS node_log_lines_ip ON node_log_lines (node, ip, at DESC);
CREATE INDEX IF NOT EXISTS node_log_lines_at ON node_log_lines (at);
-- the xray user name of a panel user (its username), looked up once
CREATE TABLE IF NOT EXISTS node_log_names (
    remnawave_id BIGINT PRIMARY KEY,
    username TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS node_log_names_username ON node_log_names (username);
-- a device watched by hand from the admin, until until_at
CREATE TABLE IF NOT EXISTS node_log_watch (
    device_id BIGINT PRIMARY KEY,
    until_at TIMESTAMPTZ NOT NULL
);

-- People turned away by app/region_filter.py (Iran): never written to users, so no statistics see them.
CREATE TABLE IF NOT EXISTS region_rejects (
    telegram_id BIGINT PRIMARY KEY,
    language TEXT,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    reason TEXT NOT NULL DEFAULT '',
    hits INTEGER NOT NULL DEFAULT 0,
    first_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    allowed_at TIMESTAMPTZ
);

-- Telegram Ads cabinet in «Рост» (app/tg_ads.py, app/tg_autobid.py).
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS ad_text TEXT NOT NULL DEFAULT '';
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS remaining NUMERIC NOT NULL DEFAULT 0;
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS daily_limit NUMERIC NOT NULL DEFAULT 0;
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS is_paused BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS placement TEXT NOT NULL DEFAULT '';
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS target JSONB;
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS schedule JSONB;
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS decline_reason TEXT;
ALTER TABLE tg_ads ADD COLUMN IF NOT EXISTS gone_at TIMESTAMPTZ;   -- no longer in the cabinet (deleted there)

-- Views, clicks and spend per 5 minutes (getAdStats): the tiles, the hours map and the autobid read these.
CREATE TABLE IF NOT EXISTS tg_ad_stats (
    ad_id BIGINT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    actions INTEGER NOT NULL DEFAULT 0,
    spent NUMERIC NOT NULL DEFAULT 0,
    PRIMARY KEY (ad_id, ts)
);
CREATE INDEX IF NOT EXISTS tg_ad_stats_ts_idx ON tg_ad_stats (ts);

-- The autobid of one ad: the lowest CPM at which it is still shown, never above max_cpm. Budgets are never touched.
CREATE TABLE IF NOT EXISTS tg_ad_autobid (
    ad_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    max_cpm NUMERIC,
    good_cpm NUMERIC,              -- the last CPM that had views
    floor_cpm NUMERIC,             -- lowering below it made the views stop; kept until floor_until
    floor_until TIMESTAMPTZ,
    base_cpm NUMERIC,              -- the CPM the autobid started from: where it goes back when raising did not help
    max_user_rub INTEGER,          -- «человек не дороже»: the bid is kept so one person from the ad costs at most this
    state TEXT NOT NULL DEFAULT 'idle',
    note TEXT NOT NULL DEFAULT '',
    changed_at TIMESTAMPTZ,
    refund_at TIMESTAMPTZ,         -- «Вернуть остаток»: paused, the rest goes back to the account after 10 minutes
    alerted JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tg_ad_log (
    id BIGSERIAL PRIMARY KEY,
    ad_id BIGINT NOT NULL,
    at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    who TEXT NOT NULL DEFAULT 'bot',
    action TEXT NOT NULL,
    old_value NUMERIC,
    new_value NUMERIC,
    note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS tg_ad_log_at_idx ON tg_ad_log (at DESC);
CREATE INDEX IF NOT EXISTS tg_ad_log_ad_idx ON tg_ad_log (ad_id, at DESC);

-- Bots and channels checked in «Разведка площадок» (getTargetBot / getTargetChannel).
CREATE TABLE IF NOT EXISTS tg_ad_places (
    username TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    audience INTEGER,
    prev_audience INTEGER,         -- the audience before the last change, to see a place losing its people
    raw JSONB,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- The first words a newcomer from this link sees in the bot, before the usual welcome.
ALTER TABLE ad_links ADD COLUMN IF NOT EXISTS greeting TEXT;
-- «Дожим»: one message an hour after coming from this link, to whoever has not connected yet (app/ad_followup.py).
ALTER TABLE ad_links ADD COLUMN IF NOT EXISTS followup TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ad_followup_at TIMESTAMPTZ;
-- The ad's status at the last alert pass: «прошло модерацию» is in_review → active.
ALTER TABLE tg_ad_autobid ADD COLUMN IF NOT EXISTS last_status TEXT;

-- Cabinet visits (app/web.py): opening the cabinet starts a visit, the cabinet's ping every 30 s while it is on screen
-- moves seen_at; a gap of more than 3 minutes starts a new one. The overview counts opens and hours from here.
CREATE TABLE IF NOT EXISTS cabinet_visits (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS cabinet_visits_user ON cabinet_visits (telegram_id, id DESC);
CREATE INDEX IF NOT EXISTS cabinet_visits_started ON cabinet_visits (started_at);
