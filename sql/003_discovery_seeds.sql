-- Discovery seed URLs for category/search pages. Step 37 – Category Seed Management.
-- Run after 001_initial_schema.sql. Safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS discovery_seeds (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    label TEXT,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discovery_seeds_enabled ON discovery_seeds(enabled);
