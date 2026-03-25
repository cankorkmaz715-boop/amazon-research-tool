#!/usr/bin/env python3
"""Step 53: Usage tracking v1 – workspace-scoped events, flow attribution, usage summary."""
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
        record_usage,
        get_usage_summary,
        get_usage_summary_for_workspace,
    )
    from amazon_research.export import export_research_csv

    init_db()

    # Ensure table exists
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_usage_events (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            payload JSONB
        );
    """)
    try:
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_workspace_usage_events_workspace_type_created
            ON workspace_usage_events(workspace_id, event_type, created_at);
        """)
    except Exception:
        pass
    conn.commit()
    cur.close()

    ws_id = create_workspace("Usage Smoke WS", slug="step53-usage-ws")

    # Workspace usage record: record events with and without workspace_id
    record_usage(ws_id, "discovery_run", {"pages": 2})
    record_usage(ws_id, "api_products")
    record_usage(None, "refresh_run")
    record_usage(ws_id, "export_csv", {"rows": 0})

    workspace_usage_ok = True  # no exception

    # Flow attribution: summary has event_type and count
    summary = get_usage_summary(workspace_id=ws_id)
    flow_attribution_ok = (
        isinstance(summary, list)
        and any(r.get("event_type") == "discovery_run" and r.get("count", 0) >= 1 for r in summary)
        and any(r.get("event_type") == "api_products" for r in summary)
        and any(r.get("event_type") == "export_csv" for r in summary)
    )

    # Usage summary: get_usage_summary_for_workspace returns dict event_type -> count
    by_ws = get_usage_summary_for_workspace(ws_id)
    usage_summary_ok = (
        isinstance(by_ws, dict)
        and by_ws.get("discovery_run", 0) >= 1
        and by_ws.get("api_products", 0) >= 1
        and by_ws.get("export_csv", 0) >= 1
    )

    # Export action records usage (optional extra check)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as f:
        export_research_csv(ws_id, f.name)
    summary_after = get_usage_summary_for_workspace(ws_id)
    export_recorded_ok = summary_after.get("export_csv", 0) >= 2  # we had 1 from above, now at least 2

    print("usage tracking OK")
    print("workspace usage record: OK" if workspace_usage_ok else "workspace usage record: FAIL")
    print("flow attribution: OK" if flow_attribution_ok else "flow attribution: FAIL")
    print("usage summary: OK" if (usage_summary_ok and export_recorded_ok) else "usage summary: FAIL")

    if not (workspace_usage_ok and flow_attribution_ok and usage_summary_ok and export_recorded_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
