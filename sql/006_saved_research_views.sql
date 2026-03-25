-- Saved research views. Step 42 – workspace-scoped, filter/sort settings stored as JSONB.
-- Run after 005_workspace_user.sql. Safe to re-run.

CREATE TABLE IF NOT EXISTS saved_research_views (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_research_views_workspace_id ON saved_research_views(workspace_id);
CREATE INDEX IF NOT EXISTS idx_saved_research_views_updated_at ON saved_research_views(updated_at);

-- settings: { "filters": { "category": "...", "asin": "..." }, "sort_by": "opportunity_score", "order": "desc" }
-- Aligns with internal API get_products / get_metrics / get_scores params where it fits.
