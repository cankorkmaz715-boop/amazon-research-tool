#!/usr/bin/env python3
"""Step 54: Quota model v1 – workspace quotas, lookup, evaluation helper, scope."""
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
        set_workspace_quota,
        get_workspace_quota,
        list_workspace_quotas,
        check_quota,
        record_usage,
    )

    init_db()

    # Ensure table exists
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_quotas (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            quota_type TEXT NOT NULL,
            limit_value INTEGER NOT NULL,
            period_days INTEGER NOT NULL DEFAULT 30,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, quota_type)
        );
    """)
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workspace_quotas_workspace_id ON workspace_quotas(workspace_id);")
    except Exception:
        pass
    conn.commit()
    cur.close()

    ws_id = create_workspace("Quota Smoke WS", slug="step54-quota-ws")

    # Quota create: set quotas for different types
    set_workspace_quota(ws_id, "discovery_run", 10, period_days=30)
    set_workspace_quota(ws_id, "export_csv", 5, period_days=7)
    quota_create_ok = True

    # Quota lookup: get one and list all
    q = get_workspace_quota(ws_id, "discovery_run")
    quota_lookup_ok = (
        q is not None
        and q.get("quota_type") == "discovery_run"
        and q.get("limit_value") == 10
        and q.get("period_days") == 30
    )
    all_q = list_workspace_quotas(ws_id)
    quota_lookup_ok = quota_lookup_ok and len(all_q) >= 2 and any(x["quota_type"] == "export_csv" for x in all_q)

    # Quota evaluation helper: check_quota returns allowed, limit, used, remaining
    record_usage(ws_id, "discovery_run")
    record_usage(ws_id, "discovery_run")
    eval_result = check_quota(ws_id, "discovery_run")
    quota_eval_ok = (
        "allowed" in eval_result
        and "limit" in eval_result
        and "used" in eval_result
        and "remaining" in eval_result
        and eval_result["limit"] == 10
        and eval_result["used"] >= 2
        and eval_result["remaining"] == 10 - eval_result["used"]
        and eval_result["allowed"] is True
    )
    # No quota set for api_products -> allowed=True, limit=None
    no_quota = check_quota(ws_id, "api_products")
    quota_eval_ok = quota_eval_ok and no_quota.get("allowed") is True and no_quota.get("limit") is None

    # Workspace scope: other workspace has no quotas
    ws2 = create_workspace("Other WS", slug="step54-quota-ws2")
    q_other = list_workspace_quotas(ws2)
    workspace_scope_ok = len(q_other) == 0 and get_workspace_quota(ws2, "discovery_run") is None

    print("quota model v1 OK")
    print("quota create: OK" if quota_create_ok else "quota create: FAIL")
    print("quota lookup: OK" if quota_lookup_ok else "quota lookup: FAIL")
    print("quota evaluation helper: OK" if quota_eval_ok else "quota evaluation helper: FAIL")
    print("workspace scope: OK" if workspace_scope_ok else "workspace scope: FAIL")

    if not (quota_create_ok and quota_lookup_ok and quota_eval_ok and workspace_scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
