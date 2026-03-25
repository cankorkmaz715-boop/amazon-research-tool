-- Plan model v1. Step 59 – subscription/plan for workspaces; quota profile and optional billing metadata.
-- Run after 005_workspace_user.sql. No payment provider logic.

CREATE TABLE IF NOT EXISTS plans (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    quota_profile JSONB,
    billing_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plans_active ON plans(active);

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS plan_id INTEGER REFERENCES plans(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_workspaces_plan_id ON workspaces(plan_id);
