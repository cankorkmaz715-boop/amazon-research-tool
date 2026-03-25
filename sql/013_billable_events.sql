-- Billable events v1. Step 58 – lightweight hooks for future billing; no payment provider.
-- Event types: usage_summary, export_csv, export_json, api_request, quota_overage.

CREATE TABLE IF NOT EXISTS billable_events (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_billable_events_workspace_created ON billable_events(workspace_id, created_at);
CREATE INDEX IF NOT EXISTS idx_billable_events_event_type ON billable_events(event_type);
