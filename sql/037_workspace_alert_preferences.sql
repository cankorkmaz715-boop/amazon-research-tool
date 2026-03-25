-- Step 198: Workspace alert preferences – per-workspace alert behavior, thresholds, delivery, quiet hours.
-- Additive only; one row per workspace (upsert by workspace_id).

CREATE TABLE IF NOT EXISTS workspace_alert_preferences (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL UNIQUE REFERENCES workspaces(id) ON DELETE CASCADE,
    alerts_enabled BOOLEAN NOT NULL DEFAULT true,
    opportunity_alerts_enabled BOOLEAN NOT NULL DEFAULT true,
    trend_alerts_enabled BOOLEAN NOT NULL DEFAULT true,
    portfolio_alerts_enabled BOOLEAN NOT NULL DEFAULT true,
    score_threshold NUMERIC(5,2) NOT NULL DEFAULT 70.0,
    priority_threshold INTEGER NOT NULL DEFAULT 0,
    delivery_channels_json JSONB DEFAULT '{}',
    quiet_hours_json JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspace_alert_preferences_workspace_id ON workspace_alert_preferences(workspace_id);
