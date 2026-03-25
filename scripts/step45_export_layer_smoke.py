#!/usr/bin/env python3
"""Step 45: Export layer – workspace-scoped CSV and JSON export."""
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
        upsert_asin,
    )
    from amazon_research.export import (
        get_research_data_for_workspace,
        export_research_csv,
        export_research_json,
    )

    init_db()

    # Ensure workspaces and asins.workspace_id exist (005)
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
        cur.execute("ALTER TABLE asins ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL")
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema check failed: {e}") from e

    wid = create_workspace("Step45 Export Test", "step45-export")
    other_wid = create_workspace("Other WS", "step45-other")
    upsert_asin("EXPORT001", title="Export Product", workspace_id=wid)

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "research.csv")
        json_path = os.path.join(tmp, "research.json")

        # CSV export
        n_csv = export_research_csv(wid, csv_path)
        csv_ok = os.path.isfile(csv_path) and n_csv >= 1
        if csv_ok:
            with open(csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            csv_ok = csv_ok and len(lines) >= 2 and "asin" in lines[0]

        # JSON export
        n_json = export_research_json(wid, json_path)
        json_ok = os.path.isfile(json_path) and n_json >= 1
        if json_ok:
            import json as _json
            with open(json_path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            json_ok = json_ok and isinstance(data, list) and len(data) >= 1 and "asin" in data[0]

        # Workspace scope: other workspace has no data
        other_data = get_research_data_for_workspace(other_wid)
        scope_ok = len(other_data) == 0 and n_csv >= 1

    print("export layer OK")
    print("csv export: OK" if csv_ok else "csv export: FAIL")
    print("json export: OK" if json_ok else "json export: FAIL")
    print("workspace scope: OK" if scope_ok else "workspace scope: FAIL")

    if not (csv_ok and json_ok and scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
