#!/usr/bin/env python3
"""Step 44: Notification rules – workspace-scoped conditions, lightweight evaluation (no delivery)."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import (
        init_db,
        get_connection,
        create_workspace,
        create_notification_rule,
        get_notification_rule,
        list_notification_rules,
        evaluate_rule,
    )

    init_db()

    # Ensure workspaces and notification_rules exist
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_rules (
                id SERIAL PRIMARY KEY,
                workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                params JSONB NOT NULL DEFAULT '{}',
                enabled BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_notification_rules_workspace_id ON notification_rules(workspace_id)")
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema ensure failed: {e}") from e

    wid = create_workspace("Step44 Rules Test", "step44-rules")
    other_wid = create_workspace("Other WS", "step44-other")

    # Rule create
    rule_id = create_notification_rule(
        wid,
        "High opportunity alert",
        "score_threshold",
        params={"score_field": "opportunity_score", "operator": ">=", "value": 70},
        enabled=True,
    )
    rule = get_notification_rule(rule_id)
    rule_create_ok = rule_id is not None and rule is not None and rule.get("rule_type") == "score_threshold"

    # Rule evaluate: score_threshold with value 80 >= 70 should match
    result = evaluate_rule(rule_id, {"event": "score_threshold", "value": 80, "score_field": "opportunity_score"})
    eval_ok = result.get("matches") is True and result.get("reason")
    # new_candidate rule: evaluate with event new_candidate
    r2_id = create_notification_rule(wid, "New candidate", "new_candidate", {})
    result2 = evaluate_rule(r2_id, {"event": "new_candidate", "asin_id": 1})
    eval_ok = eval_ok and result2.get("matches") is True

    # Workspace scope: rules in wid only
    in_workspace = list_notification_rules(wid)
    in_other = list_notification_rules(other_wid)
    workspace_scope_ok = len(in_workspace) >= 2 and any(r["id"] == rule_id for r in in_workspace) and not any(r["id"] == rule_id for r in in_other)

    print("notification rules OK")
    print("rule create: OK" if rule_create_ok else "rule create: FAIL")
    print("rule evaluate: OK" if eval_ok else "rule evaluate: FAIL")
    print("workspace scope: OK" if workspace_scope_ok else "workspace scope: FAIL")

    if not (rule_create_ok and eval_ok and workspace_scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
