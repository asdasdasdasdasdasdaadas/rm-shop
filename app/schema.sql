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

CREATE INDEX IF NOT EXISTS vpn_reports_created_at_idx ON vpn_reports (created_at DESC);

ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_rub INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS has_paid_topup BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_billed_on DATE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS platform TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS client TEXT;

CREATE TABLE IF NOT EXISTS app_flags (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

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

UPDATE users SET has_paid_topup = TRUE
WHERE telegram_id IN (
    SELECT DISTINCT telegram_id FROM rollypay_orders WHERE status = 'granted'
)
OR telegram_id IN (
    SELECT DISTINCT telegram_id FROM payments
);

