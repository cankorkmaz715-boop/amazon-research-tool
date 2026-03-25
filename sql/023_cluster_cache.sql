-- Step 103: Cluster cache layer – store computed clustering outputs for reuse.
-- Compatible with niche explorer, opportunity ranking, board, product deep analyzer.
-- Append-friendly; latest per scope_key; support invalidation via delete or overwrite-by-freshness.

CREATE TABLE IF NOT EXISTS cluster_cache (
    id SERIAL PRIMARY KEY,
    scope_key TEXT NOT NULL DEFAULT 'default',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    clusters JSONB NOT NULL DEFAULT '[]',
    summary JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_cluster_cache_scope_recorded ON cluster_cache(scope_key, recorded_at DESC);
