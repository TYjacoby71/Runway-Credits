-- Runway Credits & Incentive Intel Pack — SQLite Schema
-- Phase 1: Data & Infrastructure
-- Version: 1.0

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ─────────────────────────────────────────────
-- programs: mirrors the JSON catalog for queryability
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS programs (
    id                      TEXT PRIMARY KEY,          -- slug id e.g. "aws_activate"
    name                    TEXT NOT NULL,
    provider                TEXT NOT NULL,
    category                TEXT NOT NULL,
    credit_min_usd          INTEGER DEFAULT 0,
    credit_max_usd          INTEGER DEFAULT 0,
    realistic_credit_usd    INTEGER DEFAULT 0,
    duration_months         INTEGER,                   -- NULL = ongoing
    application_url         TEXT,
    approval_time_days      INTEGER,
    sequence_priority       INTEGER DEFAULT 3,         -- 1=apply first, 5=apply last
    conflicts_with          TEXT DEFAULT '[]',         -- JSON array of program ids
    stacks_well_with        TEXT DEFAULT '[]',         -- JSON array of program ids
    stacking_notes          TEXT,
    unlock_methods          TEXT DEFAULT '[]',         -- JSON array: "self_apply","brex_portal","yc_sus","vc_sponsor","stripe_atlas"
    tags                    TEXT DEFAULT '[]',         -- JSON array
    notes                   TEXT,
    -- eligibility fields (denormalized for fast filtering)
    elig_max_company_age_years  REAL,                  -- NULL = no limit
    elig_max_funding_usd        INTEGER,               -- NULL = no limit
    elig_max_arr_usd            INTEGER,               -- NULL = no limit
    elig_requires_us_entity     INTEGER DEFAULT 0,     -- 0/1 bool
    elig_requires_sponsor       INTEGER DEFAULT 0,     -- 0/1 bool
    elig_requires_product       INTEGER DEFAULT 0,     -- 0/1 bool
    elig_funding_stages         TEXT DEFAULT '[]',     -- JSON array of eligible stages
    elig_tech_focus             TEXT,                  -- JSON array or NULL (any)
    raw_json                    TEXT,                  -- full program object as JSON
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_programs_category ON programs(category);
CREATE INDEX IF NOT EXISTS idx_programs_sequence ON programs(sequence_priority);
CREATE INDEX IF NOT EXISTS idx_programs_credit ON programs(realistic_credit_usd DESC);

-- ─────────────────────────────────────────────
-- users: user profiles from intake form
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    email                   TEXT UNIQUE,
    name                    TEXT,
    -- company profile
    entity_type             TEXT NOT NULL,             -- "llc", "c_corp", "s_corp", "sole_proprietor", "non_us"
    company_age_years       REAL DEFAULT 0,
    funding_stage           TEXT NOT NULL,             -- "bootstrapped", "pre_seed", "seed", "series_a", "series_b_plus"
    funding_raised_usd      INTEGER DEFAULT 0,
    annual_revenue_usd      INTEGER DEFAULT 0,
    team_size               INTEGER DEFAULT 1,
    -- tech & product
    tech_stack              TEXT DEFAULT '[]',         -- JSON array: "web","ai_ml","fintech","mobile","saas","backend","frontend"
    has_deployed_product    INTEGER DEFAULT 0,         -- 0/1 bool
    -- accelerator / partner access
    has_vc_or_accelerator   INTEGER DEFAULT 0,
    accelerator_memberships TEXT DEFAULT '[]',         -- JSON array: "yc","techstars","antler","a16z", etc.
    has_brex                INTEGER DEFAULT 0,
    has_stripe_atlas        INTEGER DEFAULT 0,
    has_mercury             INTEGER DEFAULT 0,
    has_ramp                INTEGER DEFAULT 0,
    -- existing perks (program ids already held)
    current_perks           TEXT DEFAULT '[]',         -- JSON array of program ids
    -- metadata
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_funding_stage ON users(funding_stage);

-- ─────────────────────────────────────────────
-- checklists: per-user, per-program status tracking
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS checklists (
    id                      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    user_id                 TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    program_id              TEXT NOT NULL REFERENCES programs(id),
    -- match metadata
    matched                 INTEGER DEFAULT 0,         -- 0/1: was this program recommended by the engine?
    match_score             REAL DEFAULT 0,            -- computed relevance score
    match_notes             TEXT,                      -- why it was matched / ranked
    -- application status
    status                  TEXT DEFAULT 'not_started',
    -- "not_started" | "researching" | "applied" | "approved" | "rejected" | "not_eligible" | "skipped"
    applied_at              TEXT,
    approved_at             TEXT,
    -- affiliate tracking
    affiliate_link          TEXT,                      -- user's personal referral/affiliate link for this program
    affiliate_notes         TEXT,
    -- notes & tracking
    user_notes              TEXT,
    reminder_date           TEXT,                      -- ISO date for follow-up reminder
    credit_amount_received  INTEGER,                   -- actual credits received (may differ from catalog estimate)
    -- metadata
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, program_id)
);

CREATE INDEX IF NOT EXISTS idx_checklists_user ON checklists(user_id);
CREATE INDEX IF NOT EXISTS idx_checklists_program ON checklists(program_id);
CREATE INDEX IF NOT EXISTS idx_checklists_status ON checklists(user_id, status);
CREATE INDEX IF NOT EXISTS idx_checklists_matched ON checklists(user_id, matched, match_score DESC);

-- ─────────────────────────────────────────────
-- stacking_rules: explicit known stacking relationships
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stacking_rules (
    id                      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    program_a               TEXT NOT NULL REFERENCES programs(id),
    program_b               TEXT NOT NULL REFERENCES programs(id),
    relationship            TEXT NOT NULL,             -- "conflicts" | "stacks_well" | "prerequisite" | "unlocks"
    notes                   TEXT,
    compound_value_usd      INTEGER,                   -- estimated extra value from stacking A+B
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_stacking_a ON stacking_rules(program_a, relationship);
CREATE INDEX IF NOT EXISTS idx_stacking_b ON stacking_rules(program_b, relationship);

-- ─────────────────────────────────────────────
-- schema version tracker
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT DEFAULT (datetime('now')),
    notes       TEXT
);

INSERT OR IGNORE INTO schema_version (version, notes) VALUES (1, 'Initial schema: programs, users, checklists, stacking_rules');
