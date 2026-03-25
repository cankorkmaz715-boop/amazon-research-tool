-- Step 236: Opportunity feed persistence & history – current state and history snapshots.
-- Current: one row per (workspace_id, opportunity_ref). History: append-only for timeline/trend.

CREATE TABLE IF NOT EXISTS opportunity_feed_current (
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    opportunity_ref TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, opportunity_ref)
);

CREATE INDEX IF NOT EXISTS idx_opportunity_feed_current_workspace ON opportunity_feed_current(workspace_id);
CREATE INDEX IF NOT EXISTS idx_opportunity_feed_current_updated ON opportunity_feed_current(workspace_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS opportunity_feed_history (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    opportunity_ref TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opportunity_feed_history_workspace ON opportunity_feed_history(workspace_id);
CREATE INDEX IF NOT EXISTS idx_opportunity_feed_history_observed ON opportunity_feed_history(workspace_id, observed_at DESC);
