-- Workspace-scoped API keys. Step 51 – tenant auth; keys stored hashed; multiple keys per workspace.
-- Run after 005_workspace_user.sql. Safe to re-run.

CREATE TABLE IF NOT EXISTS workspace_api_keys (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    label TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_api_keys_hash ON workspace_api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_workspace_api_keys_workspace_id ON workspace_api_keys(workspace_id);
