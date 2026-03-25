-- Step 216: Add read_at to opportunity_alerts for Alert Center mark-as-read.
-- Additive only; no destructive changes.

ALTER TABLE opportunity_alerts ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_opportunity_alerts_read_at ON opportunity_alerts(read_at) WHERE read_at IS NOT NULL;
