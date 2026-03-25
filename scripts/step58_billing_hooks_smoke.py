#!/usr/bin/env python3
"""Step 58: Billing hooks v1 – billable event create, workspace scope, billing summary hook."""
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
        record_billable_event,
        get_billable_events_summary,
        record_usage_summary_billable,
        record_usage,
    )

    init_db()

    # Ensure table exists
    cur = get_connection().cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billable_events (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata JSONB
        );
    """)
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_billable_events_workspace_created ON billable_events(workspace_id, created_at);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_billable_events_event_type ON billable_events(event_type);")
    except Exception:
        pass
    get_connection().commit()
    cur.close()

    ws1 = create_workspace("Billing WS 1", slug="step58-billing-ws1")
    ws2 = create_workspace("Billing WS 2", slug="step58-billing-ws2")

    # Billable event create
    record_billable_event(ws1, "export_csv", {"rows": 5})
    record_billable_event(ws1, "api_request", {"endpoint": "products"})
    record_billable_event(ws1, "quota_overage", {"quota_type": "export_csv", "limit": 10, "used": 10})
    billable_create_ok = True  # no exception

    # Workspace scope: ws2 has no events; summary for ws1 has our events
    summary_ws1 = get_billable_events_summary(ws1)
    summary_ws2 = get_billable_events_summary(ws2)
    workspace_scope_ok = (
        len(summary_ws2) == 0
        and any(r["event_type"] == "export_csv" and r["count"] >= 1 for r in summary_ws1)
        and any(r["event_type"] == "api_request" for r in summary_ws1)
        and any(r["event_type"] == "quota_overage" for r in summary_ws1)
    )

    # Billing summary hook: record_usage_summary_billable records usage_summary event
    record_usage(ws1, "export_csv")
    record_usage(ws1, "api_products")
    record_usage_summary_billable(ws1, since_days=30)
    summary_after = get_billable_events_summary(ws1)
    billing_summary_ok = any(r["event_type"] == "usage_summary" and r["count"] >= 1 for r in summary_after)

    print("billing hooks v1 OK")
    print("billable event create: OK" if billable_create_ok else "billable event create: FAIL")
    print("workspace scope: OK" if workspace_scope_ok else "workspace scope: FAIL")
    print("billing summary hook: OK" if billing_summary_ok else "billing summary hook: FAIL")

    if not (billable_create_ok and workspace_scope_ok and billing_summary_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
