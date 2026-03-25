-- Delayed job scheduling v1. Step 64 – jobs not run before scheduled_at (not_before).
-- Run after 016_worker_jobs_retry.sql.

ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_worker_jobs_scheduled_at ON worker_jobs(scheduled_at) WHERE status = 'pending';
