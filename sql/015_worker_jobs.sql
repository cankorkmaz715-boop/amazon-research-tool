-- Worker queue foundation. Step 61 – jobs for discovery, refresh, scoring; status and timestamps.
-- Run after 005_workspace_user.sql. Minimal local queue; extend later for multi-worker.

CREATE TABLE IF NOT EXISTS worker_jobs (
    id SERIAL PRIMARY KEY,
    job_type TEXT NOT NULL,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    payload JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_worker_jobs_status_type ON worker_jobs(status, job_type);
CREATE INDEX IF NOT EXISTS idx_worker_jobs_workspace ON worker_jobs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_worker_jobs_created ON worker_jobs(created_at);
