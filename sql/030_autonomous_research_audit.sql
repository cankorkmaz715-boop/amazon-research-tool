-- Step 139: Autonomous research audit trail – record key decisions and actions from controlled autonomous runs.
-- Append-friendly; payload stores run_id, actions, safety, opportunities summary, timestamps.

CREATE TABLE IF NOT EXISTS autonomous_research_audit (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_autonomous_research_audit_run_id ON autonomous_research_audit(run_id);
CREATE INDEX IF NOT EXISTS idx_autonomous_research_audit_workspace_created ON autonomous_research_audit(workspace_id, created_at DESC);
