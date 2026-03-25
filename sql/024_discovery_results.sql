-- Step 104: Discovery result storage – persist scan outputs for reuse.
-- Compatible with category/keyword scanner, automated niche discovery, reverse ASIN, dashboard.
-- Append-friendly; history per source_type/source_id.

CREATE TABLE IF NOT EXISTS discovery_results (
    id SERIAL PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    marketplace TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    asins JSONB NOT NULL DEFAULT '[]',
    scan_metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_discovery_results_source ON discovery_results(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_discovery_results_recorded ON discovery_results(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_discovery_results_asins_gin ON discovery_results USING GIN (asins);
