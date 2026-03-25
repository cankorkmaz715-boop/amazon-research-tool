#!/usr/bin/env python3
"""Step 55: Quota enforcement v1 – within quota OK, over quota blocked, clear result, workspace scope."""
import os
import sys
import tempfile

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
        check_quota_and_raise,
        QuotaExceededError,
    )
    from amazon_research.export import export_research_csv

    init_db()

    # Ensure quota table exists
    cur = get_connection().cursor()
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
    get_connection().commit()
    cur.close()

    ws1 = create_workspace("Enforce WS 1", slug="step55-enforce-ws1")
    ws2 = create_workspace("Enforce WS 2", slug="step55-enforce-ws2")

    # Within quota: set limit 2, first export succeeds
    set_workspace_quota(ws1, "export_csv", 2, period_days=30)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as f:
        n = export_research_csv(ws1, f.name)
    within_quota_ok = n is not None  # no exception

    # Over quota blocked: second export (same workspace) still under 2; do two more to exceed
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as f:
        export_research_csv(ws1, f.name)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as f:
        export_research_csv(ws1, f.name)
    # Now used=3, limit=2. Next export should raise.
    over_blocked_ok = False
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as f:
            export_research_csv(ws1, f.name)
    except QuotaExceededError as e:
        over_blocked_ok = e.quota_type == "export_csv" and e.limit == 2 and e.used >= 2 and e.remaining == 0

    # Clear quota result: exception has quota_type, limit, used, remaining
    clear_result_ok = over_blocked_ok  # already asserted above; optionally catch again and check message
    try:
        check_quota_and_raise(ws1, "export_csv")
    except QuotaExceededError as e:
        clear_result_ok = (
            clear_result_ok
            and hasattr(e, "quota_type") and e.quota_type == "export_csv"
            and hasattr(e, "limit") and hasattr(e, "used") and hasattr(e, "remaining")
        )

    # Workspace scope: ws1 discovery_run quota 0 -> check_quota_and_raise raises; ws2 quota 100 -> no raise; ws2 export no quota -> allowed
    set_workspace_quota(ws1, "discovery_run", 0, period_days=30)
    set_workspace_quota(ws2, "discovery_run", 100, period_days=30)
    try:
        check_quota_and_raise(ws1, "discovery_run")
        workspace_scope_ok = False  # should have raised
    except QuotaExceededError:
        workspace_scope_ok = True
    check_quota_and_raise(ws2, "discovery_run")  # no raise
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as f:
        export_research_csv(ws2, f.name)  # ws2 has no export_csv quota -> allowed
    workspace_scope_ok = workspace_scope_ok and True

    print("quota enforcement v1 OK")
    print("within quota: OK" if within_quota_ok else "within quota: FAIL")
    print("over quota blocked: OK" if over_blocked_ok else "over quota blocked: FAIL")
    print("clear quota result: OK" if clear_result_ok else "clear quota result: FAIL")
    print("workspace scope: OK" if workspace_scope_ok else "workspace scope: FAIL")

    if not (within_quota_ok and over_blocked_ok and clear_result_ok and workspace_scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
