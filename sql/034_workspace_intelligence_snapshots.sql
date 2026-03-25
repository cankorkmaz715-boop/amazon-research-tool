-- Step 192: Workspace intelligence snapshots – persist workspace intelligence summaries for fast, stable reads.
-- Additive only; append-only writes. Payload: full summary object (workspace_id, summary_timestamp, totals, etc.).

CREATE TABLE IF NOT EXISTS workspace_intelligence_snapshots (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    snapshot_type TEXT NOT NULL DEFAULT 'summary',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    summary_json JSONB NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspace_intelligence_snapshots_workspace_id ON workspace_intelligence_snapshots(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_intelligence_snapshots_generated_at ON workspace_intelligence_snapshots(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_workspace_intelligence_snapshots_workspace_generated ON workspace_intelligence_snapshots(workspace_id, generated_at DESC);
