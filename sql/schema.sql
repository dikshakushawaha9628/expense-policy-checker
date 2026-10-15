-- =====================================================================
-- Data model (SQLite).  Layers: RAW -> CURATED -> RULES / AI
--   raw_expenses      immutable copy of what the file said (all TEXT)
--   expenses          cleaned, typed, constrained records
--   rejected_records  rows that failed cleaning, with the reason
--   rule_violations   DETERMINISTIC policy failures
--   ai_observations   ADVISORY model output (kept in a separate table on purpose)
-- =====================================================================
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingest_batches (
    batch_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file           TEXT NOT NULL,
    loaded_at             TEXT NOT NULL,
    rows_read             INTEGER NOT NULL DEFAULT 0,
    rows_new              INTEGER NOT NULL DEFAULT 0,
    rows_skipped_existing INTEGER NOT NULL DEFAULT 0,
    rows_rejected         INTEGER NOT NULL DEFAULT 0
);

-- RAW layer: everything is TEXT so nothing can be lost to a type error.
-- row_hash UNIQUE makes re-ingesting the same file idempotent.
CREATE TABLE IF NOT EXISTS raw_expenses (
    raw_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id         INTEGER NOT NULL REFERENCES ingest_batches(batch_id),
    row_hash         TEXT NOT NULL UNIQUE,
    expense_id       TEXT,
    employee_id      TEXT,
    expense_date     TEXT,
    submitted_date   TEXT,
    merchant         TEXT,
    category         TEXT,
    amount           TEXT,
    currency         TEXT,
    description      TEXT,
    receipt_attached TEXT,
    approver_id      TEXT
);

CREATE TABLE IF NOT EXISTS fx_rates (
    currency    TEXT PRIMARY KEY,
    rate_to_usd REAL NOT NULL CHECK (rate_to_usd > 0)
);

-- CURATED layer: typed + constrained.
CREATE TABLE IF NOT EXISTS expenses (
    expense_id       TEXT PRIMARY KEY,
    raw_id           INTEGER NOT NULL REFERENCES raw_expenses(raw_id),
    employee_id      TEXT NOT NULL,
    expense_date     TEXT NOT NULL CHECK (expense_date   GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    submitted_date   TEXT NOT NULL CHECK (submitted_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    merchant         TEXT NOT NULL,
    category         TEXT NOT NULL CHECK (category IN (
        'Meals','Lodging','Airfare','Ground Transport','Office Supplies',
        'Software','Entertainment','Alcohol','Personal')),
    amount           REAL NOT NULL CHECK (amount > 0),
    currency         TEXT NOT NULL REFERENCES fx_rates(currency),
    description      TEXT NOT NULL DEFAULT '',
    receipt_attached INTEGER NOT NULL CHECK (receipt_attached IN (0,1)),
    approver_id      TEXT
);
CREATE INDEX IF NOT EXISTS ix_expenses_employee ON expenses(employee_id, expense_date);

CREATE TABLE IF NOT EXISTS rejected_records (
    reject_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id   INTEGER NOT NULL REFERENCES ingest_batches(batch_id),
    raw_id     INTEGER NOT NULL REFERENCES raw_expenses(raw_id),
    expense_id TEXT,
    reason     TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- DETERMINISTIC results. Fully recomputed on every `check`, so it is idempotent.
CREATE TABLE IF NOT EXISTS rule_violations (
    expense_id     TEXT NOT NULL REFERENCES expenses(expense_id),
    rule_id        TEXT NOT NULL,
    severity       TEXT NOT NULL CHECK (severity IN ('low','medium','high')),
    message        TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    evaluated_at   TEXT NOT NULL,
    PRIMARY KEY (expense_id, rule_id)
);

-- ADVISORY results. Never joined into pass/fail logic.
CREATE TABLE IF NOT EXISTS ai_observations (
    obs_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id         TEXT NOT NULL REFERENCES expenses(expense_id),
    provider           TEXT NOT NULL,
    model              TEXT NOT NULL,
    prompt_version     TEXT NOT NULL,
    status             TEXT NOT NULL CHECK (status IN ('ok','low_confidence','invalid_response','error')),
    label              TEXT,
    confidence         REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    rationale          TEXT,
    needs_human_review INTEGER NOT NULL CHECK (needs_human_review IN (0,1)),
    created_at         TEXT NOT NULL,
    UNIQUE (expense_id, provider, prompt_version)
);
