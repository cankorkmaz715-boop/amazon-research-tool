-- Step 197: Workspace portfolio items – explicit tracking of opportunities, ASINs, niches, categories, markets, keywords.
-- Additive only. Deduplication by (workspace_id, item_type, item_key).

CREATE TABLE IF NOT EXISTS workspace_portfolio_items (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL,
    item_key TEXT NOT NULL,
    item_label TEXT,
    source_type TEXT,
    metadata_json JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, item_type, item_key)
);

CREATE INDEX IF NOT EXISTS idx_workspace_portfolio_items_workspace ON workspace_portfolio_items(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_portfolio_items_type ON workspace_portfolio_items(item_type);
CREATE INDEX IF NOT EXISTS idx_workspace_portfolio_items_status ON workspace_portfolio_items(status);
