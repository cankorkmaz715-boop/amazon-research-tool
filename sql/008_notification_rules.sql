-- Notification rules. Step 44 – workspace-scoped, lightweight conditions. No delivery in this step.
-- Run after 005_workspace_user.sql (and 007_watchlists.sql for watchlist_id in params). Safe to re-run.

CREATE TABLE IF NOT EXISTS notification_rules (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    params JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_rules_workspace_id ON notification_rules(workspace_id);
CREATE INDEX IF NOT EXISTS idx_notification_rules_rule_type ON notification_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_notification_rules_enabled ON notification_rules(enabled);

-- rule_type: 'score_threshold' | 'new_candidate' | 'tracked_updated'
-- params examples:
--   score_threshold: { "score_field": "opportunity_score", "operator": ">=", "value": 70 }
--   new_candidate: {}
--   tracked_updated: { "watchlist_id": 1 }
