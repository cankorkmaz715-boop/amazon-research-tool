-- Step 107: Opportunity alerts – persist detected alerts for dashboard and notification rules.
-- Lightweight; alert engine produces in-memory alerts; optional save for listing/filtering.

CREATE TABLE IF NOT EXISTS opportunity_alerts (
    id SERIAL PRIMARY KEY,
    target_type TEXT NOT NULL DEFAULT 'cluster',
    target_entity TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    triggering_signals JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_opportunity_alerts_target ON opportunity_alerts(target_type, target_entity);
CREATE INDEX IF NOT EXISTS idx_opportunity_alerts_recorded ON opportunity_alerts(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_opportunity_alerts_type ON opportunity_alerts(alert_type);
