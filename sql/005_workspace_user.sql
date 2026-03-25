-- User / Workspace model v1. Step 41 – internal-first, minimal, SaaS-ready later.
-- Run after 001_initial_schema.sql and 003_discovery_seeds.sql. Safe to re-run.

-- Workspaces: tenant/org container
CREATE TABLE IF NOT EXISTS workspaces (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON workspaces(slug);

-- Users: linked to a workspace (no auth/signup in this step)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    identifier TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, identifier)
);

CREATE INDEX IF NOT EXISTS idx_users_workspace_id ON users(workspace_id);

-- Prepare core entities: nullable workspace_id (existing rows stay NULL = single-tenant)
ALTER TABLE asins ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_asins_workspace_id ON asins(workspace_id);

ALTER TABLE discovery_seeds ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_discovery_seeds_workspace_id ON discovery_seeds(workspace_id);
