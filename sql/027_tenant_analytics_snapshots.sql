-- Step 116: Tenant analytics snapshots – periodic workspace-level analytics summaries.
-- History-friendly, append-only. Payload: usage_summary, quota_status, cost_insight_summary, etc.

CREATE TABLE IF NOT EXISTS tenant_analytics_snapshots (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    since_days INTEGER,
    payload JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_tenant_analytics_snapshots_workspace_at ON tenant_analytics_snapshots(workspace_id, snapshot_at DESC);
