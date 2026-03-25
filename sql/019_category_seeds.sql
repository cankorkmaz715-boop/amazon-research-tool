-- Category seed manager v1. Step 73 – marketplace, category URL, label, active, last_scanned_at, scan_metadata.
-- Run after 005_workspace_user.sql (workspaces). Workspace-aware; optional workspace_id.
-- One row per category_url (workspace_id for filtering only).

CREATE TABLE IF NOT EXISTS category_seeds (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    marketplace TEXT NOT NULL DEFAULT 'DE',
    category_url TEXT NOT NULL UNIQUE,
    label TEXT,
    active BOOLEAN NOT NULL DEFAULT true,
    last_scanned_at TIMESTAMPTZ,
    scan_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_category_seeds_active ON category_seeds(active);
CREATE INDEX IF NOT EXISTS idx_category_seeds_workspace ON category_seeds(workspace_id);
CREATE INDEX IF NOT EXISTS idx_category_seeds_last_scanned ON category_seeds(last_scanned_at);
