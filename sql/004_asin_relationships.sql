-- ASIN-to-ASIN relationship graph. Step 38 – ASIN Relationship Graph v1.
-- Run after 001_initial_schema.sql. Safe to re-run (IF NOT EXISTS).
-- source_type: e.g. 'related', 'sponsored', 'seed' – application-defined label.

CREATE TABLE IF NOT EXISTS asin_relationships (
    id SERIAL PRIMARY KEY,
    from_asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
    to_asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL DEFAULT 'related',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(from_asin_id, to_asin_id, source_type)
);

CREATE INDEX IF NOT EXISTS idx_asin_relationships_from ON asin_relationships(from_asin_id);
CREATE INDEX IF NOT EXISTS idx_asin_relationships_to ON asin_relationships(to_asin_id);
CREATE INDEX IF NOT EXISTS idx_asin_relationships_source_type ON asin_relationships(source_type);
