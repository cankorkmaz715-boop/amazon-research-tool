-- Step 131: Portfolio watch engine – register and track ASIN, keyword, niche, cluster over time.
-- last_snapshot stores previous state for change detection.

CREATE TABLE IF NOT EXISTS portfolio_watches (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    last_snapshot JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_watches_workspace ON portfolio_watches(workspace_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_watches_target ON portfolio_watches(target_type, target_ref);
CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_watches_workspace_target ON portfolio_watches(workspace_id, target_type, target_ref);
