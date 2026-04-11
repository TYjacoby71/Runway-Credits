-- Runway Credits — Schema v2 Migration
-- Adds analytics events + revenue events for Intel Pack KPI tracking
-- Apply with: python setup_db.py --migrate

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ─────────────────────────────────────────────
-- analytics_events: fine-grained event log
-- tracks: signup, match_run, checklist_generated, api_call, affiliate_click, tier_upgrade
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analytics_events (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    event_type      TEXT NOT NULL,
    -- "signup"              user profile submitted (self-serve UI or CLI)
    -- "match_run"           /match endpoint called (anonymous or identified)
    -- "checklist_generated" /checklist/generate called + persisted
    -- "api_call"            any agent API call (logged per request)
    -- "affiliate_click"     user clicked an affiliate link from their checklist
    -- "tier_upgrade"        free -> paid conversion event
    user_id         TEXT REFERENCES users(id),         -- NULL for anonymous
    user_email      TEXT,                               -- denormalized for fast lookup
    caller_type     TEXT DEFAULT 'web_ui',              -- "web_ui" | "agent_api" | "cli"
    caller_agent    TEXT,                               -- agent id / name if caller_type=agent_api
    endpoint        TEXT,                               -- HTTP path if caller_type=agent_api
    program_id      TEXT REFERENCES programs(id),       -- for affiliate_click events
    metadata        TEXT DEFAULT '{}',                  -- JSON blob for extra context
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_user       ON analytics_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_caller     ON analytics_events(caller_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_date       ON analytics_events(created_at DESC);

-- ─────────────────────────────────────────────
-- revenue_events: payment / subscription records
-- Stripe webhooks will populate this once credentials are provided.
-- Until then, manual entries are supported.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS revenue_events (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    event_type          TEXT NOT NULL,
    -- "one_time_payment"    single Intel Pack purchase
    -- "subscription_start"  agent API monthly subscription started
    -- "subscription_renew"  monthly renewal
    -- "subscription_cancel" cancellation
    -- "refund"              payment reversed
    user_id             TEXT REFERENCES users(id),
    user_email          TEXT,
    amount_cents        INTEGER NOT NULL DEFAULT 0,     -- positive = revenue, negative = refund
    currency            TEXT DEFAULT 'usd',
    sku                 TEXT NOT NULL DEFAULT 'intel_pack',
    -- "intel_pack_one_time"    $997-$1497
    -- "agent_api_monthly"      $99-$299/mo
    -- "affiliate_commission"   passive income from referrals
    tier                TEXT,                           -- "standard" | "pro" | "enterprise"
    stripe_payment_id   TEXT UNIQUE,                    -- Stripe payment_intent/charge id (NULL until Stripe live)
    stripe_subscription TEXT,                           -- Stripe subscription id for recurring
    source              TEXT DEFAULT 'manual',          -- "stripe_webhook" | "manual"
    notes               TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_revenue_sku      ON revenue_events(sku, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_type     ON revenue_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_user     ON revenue_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_date     ON revenue_events(created_at DESC);

-- ─────────────────────────────────────────────
-- schema version bump
-- ─────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, notes)
VALUES (2, 'Analytics events + revenue events tables for Intel Pack KPI tracking');
