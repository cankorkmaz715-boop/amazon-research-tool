-- Workspace quota model v1. Step 54 – limits per quota type; integrates with usage tracking.
-- Run after 010_workspace_usage_events.sql. Quota types align with usage event_type.

CREATE TABLE IF NOT EXISTS workspace_quotas (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    quota_type TEXT NOT NULL,
    limit_value INTEGER NOT NULL,
    period_days INTEGER NOT NULL DEFAULT 30,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, quota_type)
);

CREATE INDEX IF NOT EXISTS idx_workspace_quotas_workspace_id ON workspace_quotas(workspace_id);
