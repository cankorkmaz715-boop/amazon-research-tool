-- Retry orchestration v1. Step 63 – retry_count, max_retries, next_retry_at; final failed after exhaustion.
-- Run after 015_worker_jobs.sql.

ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3;
ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_worker_jobs_next_retry ON worker_jobs(next_retry_at) WHERE status = 'pending';
