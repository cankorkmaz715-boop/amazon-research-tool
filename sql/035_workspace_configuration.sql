-- Step 196: Workspace configuration – per-workspace operational settings for intelligence, refresh, cache, alerts.
-- Additive only; one row per workspace (upsert by workspace_id).

CREATE TABLE IF NOT EXISTS workspace_configuration (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL UNIQUE REFERENCES workspaces(id) ON DELETE CASCADE,
    intelligence_refresh_enabled BOOLEAN NOT NULL DEFAULT true,
    intelligence_refresh_interval_minutes INTEGER NOT NULL DEFAULT 60,
    intelligence_cache_enabled BOOLEAN NOT NULL DEFAULT true,
    intelligence_cache_ttl_seconds INTEGER NOT NULL DEFAULT 300,
    alerts_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspace_configuration_workspace_id ON workspace_configuration(workspace_id);
