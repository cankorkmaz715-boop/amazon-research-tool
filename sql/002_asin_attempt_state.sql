-- Failure tracking and retry state (Step 22). One row per ASIN; skip_until = temporarily skippable.
CREATE TABLE IF NOT EXISTS asin_attempt_state (
    asin_id INTEGER PRIMARY KEY REFERENCES asins(id) ON DELETE CASCADE,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    skip_until TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asin_attempt_state_skip_until ON asin_attempt_state(skip_until) WHERE skip_until IS NOT NULL;
