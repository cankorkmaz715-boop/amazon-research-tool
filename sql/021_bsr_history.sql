-- Step 101: BSR history engine – append-only historical rank/BSR for trend and opportunity analysis.
-- Used by trend engine, trend scoring, demand signals, opportunity analysis.

CREATE TABLE IF NOT EXISTS bsr_history (
    id SERIAL PRIMARY KEY,
    asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    marketplace TEXT NOT NULL DEFAULT 'DE',
    bsr TEXT,
    category_context TEXT
);

CREATE INDEX IF NOT EXISTS idx_bsr_history_asin_id ON bsr_history(asin_id);
CREATE INDEX IF NOT EXISTS idx_bsr_history_recorded_at ON bsr_history(recorded_at);
