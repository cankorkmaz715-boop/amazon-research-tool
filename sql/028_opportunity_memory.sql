-- Step 124: Opportunity memory – store discovered opportunity candidates over time.
-- Tracks first_seen_at, last_seen_at, score evolution, status (newly_discovered, recurring, strengthening, weakening).

CREATE TABLE IF NOT EXISTS opportunity_memory (
    id SERIAL PRIMARY KEY,
    opportunity_ref TEXT NOT NULL,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    context JSONB DEFAULT '{}',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latest_opportunity_score NUMERIC,
    score_history JSONB DEFAULT '[]',
    alert_summary JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'newly_discovered',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(opportunity_ref)
);

CREATE INDEX IF NOT EXISTS idx_opportunity_memory_ref ON opportunity_memory(opportunity_ref);
CREATE INDEX IF NOT EXISTS idx_opportunity_memory_last_seen ON opportunity_memory(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_opportunity_memory_status ON opportunity_memory(status);
CREATE INDEX IF NOT EXISTS idx_opportunity_memory_workspace ON opportunity_memory(workspace_id) WHERE workspace_id IS NOT NULL;
