-- Step 106: Reverse ASIN keyword graph – edges between ASINs and keywords.
-- Used by reverse ASIN analysis, advanced keyword expansion, automated niche discovery.
-- Append-friendly; source context and marketplace for explainability.

CREATE TABLE IF NOT EXISTS asin_keyword_edges (
    id SERIAL PRIMARY KEY,
    asin TEXT NOT NULL,
    keyword TEXT NOT NULL,
    source_context TEXT NOT NULL DEFAULT 'keyword_scan',
    marketplace TEXT DEFAULT 'DE',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asin_keyword_edges_asin ON asin_keyword_edges(asin);
CREATE INDEX IF NOT EXISTS idx_asin_keyword_edges_keyword ON asin_keyword_edges(keyword);
CREATE INDEX IF NOT EXISTS idx_asin_keyword_edges_recorded ON asin_keyword_edges(recorded_at DESC);
