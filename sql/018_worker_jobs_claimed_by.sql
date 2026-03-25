-- Multi-worker readiness v1. Step 66 – worker identity; safe job claiming.
-- Run after 017_worker_jobs_scheduled_at.sql.

ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS claimed_by TEXT;

CREATE INDEX IF NOT EXISTS idx_worker_jobs_claimed_by ON worker_jobs(claimed_by) WHERE status = 'running';
