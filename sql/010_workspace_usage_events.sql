-- Workspace usage tracking v1. Step 53 – discovery, refresh, scoring, export, API access.
-- Run after 005_workspace_user.sql. workspace_id NULL = system-level (e.g. pipeline).

CREATE TABLE IF NOT EXISTS workspace_usage_events (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_workspace_usage_events_workspace_type_created
    ON workspace_usage_events(workspace_id, event_type, created_at);
