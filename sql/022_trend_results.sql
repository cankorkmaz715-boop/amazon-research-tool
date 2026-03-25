-- Step 102: Trend data persistence – store computed trend signals for reuse.
-- Append-friendly; each row is one snapshot. Used by niche scoring, ranking, board, dashboard.

CREATE TABLE IF NOT EXISTS trend_results (
    id SERIAL PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    asin_id INTEGER REFERENCES asins(id) ON DELETE SET NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    marketplace TEXT,
    signals JSONB NOT NULL DEFAULT '{}',
    explanation TEXT
);

CREATE INDEX IF NOT EXISTS idx_trend_results_target ON trend_results(target_type, target_ref);
CREATE INDEX IF NOT EXISTS idx_trend_results_recorded_at ON trend_results(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_trend_results_asin_id ON trend_results(asin_id) WHERE asin_id IS NOT NULL;
