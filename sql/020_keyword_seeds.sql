-- Keyword seed manager v1. Step 77 – marketplace, keyword, label, active, last_scanned_at, scan_metadata.
-- Run after 005_workspace_user.sql (workspaces). Workspace-aware; optional workspace_id.
-- One row per keyword (workspace_id for filtering only).

CREATE TABLE IF NOT EXISTS keyword_seeds (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    marketplace TEXT NOT NULL DEFAULT 'DE',
    keyword TEXT NOT NULL UNIQUE,
    label TEXT,
    active BOOLEAN NOT NULL DEFAULT true,
    last_scanned_at TIMESTAMPTZ,
    scan_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_keyword_seeds_active ON keyword_seeds(active);
CREATE INDEX IF NOT EXISTS idx_keyword_seeds_workspace ON keyword_seeds(workspace_id);
CREATE INDEX IF NOT EXISTS idx_keyword_seeds_last_scanned ON keyword_seeds(last_scanned_at);
