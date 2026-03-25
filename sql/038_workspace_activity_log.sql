-- Step 199: Workspace activity log – structured workspace events for debugging, audit, dashboard timeline.
-- Additive only. Activity logging must not block primary flows.

CREATE TABLE IF NOT EXISTS workspace_activity_log (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_label TEXT,
    actor_type TEXT,
    actor_id TEXT,
    source_module TEXT,
    event_payload_json JSONB DEFAULT '{}',
    severity TEXT NOT NULL DEFAULT 'info',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspace_activity_log_workspace_id ON workspace_activity_log(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_activity_log_created_at ON workspace_activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workspace_activity_log_workspace_created ON workspace_activity_log(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workspace_activity_log_event_type ON workspace_activity_log(event_type);
