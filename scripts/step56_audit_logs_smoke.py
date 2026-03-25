#!/usr/bin/env python3
"""Step 56: Audit logs v1 – log create, workspace scoped, event recorded."""
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
        record_audit,
        list_audit_logs,
    )
    from amazon_research.export import export_research_csv

    init_db()

    # Ensure table exists
    cur = get_connection().cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata JSONB
        );
    """)
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_workspace_created ON audit_logs(workspace_id, created_at);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);")
    except Exception:
        pass
    get_connection().commit()
    cur.close()

    ws1 = create_workspace("Audit WS 1", slug="step56-audit-ws1")
    ws2 = create_workspace("Audit WS 2", slug="step56-audit-ws2")

    # Log create: record_audit succeeds
    record_audit(ws1, "discovery_run", {"asins_count": 5})
    record_audit(ws1, "export_csv", {"rows": 10})
    record_audit(ws2, "api_products")
    log_create_ok = True  # no exception

    # Workspace scoped: list_audit_logs(ws1) returns only ws1 entries
    ws1_logs = list_audit_logs(workspace_id=ws1)
    workspace_scoped_ok = all(e.get("workspace_id") == ws1 for e in ws1_logs) and len(ws1_logs) >= 2

    # Event recorded: expected event_types present
    all_ws1_types = {e.get("event_type") for e in ws1_logs}
    event_recorded_ok = "discovery_run" in all_ws1_types and "export_csv" in all_ws1_types
    # Export action also writes audit
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as f:
        export_research_csv(ws1, f.name)
    ws1_after = list_audit_logs(workspace_id=ws1)
    export_audit_count = sum(1 for e in ws1_after if e.get("event_type") == "export_csv")
    event_recorded_ok = event_recorded_ok and export_audit_count >= 2

    print("audit logs v1 OK")
    print("log create: OK" if log_create_ok else "log create: FAIL")
    print("workspace scoped: OK" if workspace_scoped_ok else "workspace scoped: FAIL")
    print("event recorded: OK" if event_recorded_ok else "event recorded: FAIL")

    if not (log_create_ok and workspace_scoped_ok and event_recorded_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
