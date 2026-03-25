#!/usr/bin/env python3
"""Step 42: Saved research views – workspace-scoped filter/sort presets."""
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
        create_saved_view,
        get_saved_view,
        list_saved_views,
    )

    init_db()

    # Ensure workspaces and saved_research_views exist
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
            CREATE TABLE IF NOT EXISTS saved_research_views (
                id SERIAL PRIMARY KEY,
                workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                settings JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_saved_research_views_workspace_id ON saved_research_views(workspace_id)")
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema ensure failed: {e}") from e

    # Workspace for scoping
    wid = create_workspace("Step42 Views Test", "step42-views")
    other_wid = create_workspace("Other Workspace", "step42-other")

    # View create
    settings = {"filters": {"category": "Electronics"}, "sort_by": "opportunity_score", "order": "desc"}
    view_id = create_saved_view(wid, "High opportunity electronics", settings)
    view_create_ok = view_id is not None and view_id >= 1

    # View load
    loaded = get_saved_view(view_id)
    view_load_ok = (
        loaded is not None
        and loaded.get("name") == "High opportunity electronics"
        and loaded.get("settings", {}).get("sort_by") == "opportunity_score"
        and loaded.get("workspace_id") == wid
    )

    # Workspace scope: view belongs to wid; list for wid returns it, list for other_wid does not
    in_workspace = list_saved_views(wid)
    in_other = list_saved_views(other_wid)
    workspace_scope_ok = (
        len(in_workspace) >= 1
        and any(v["id"] == view_id for v in in_workspace)
        and not any(v["id"] == view_id for v in in_other)
    )

    print("saved research views OK")
    print("view create: OK" if view_create_ok else "view create: FAIL")
    print("view load: OK" if view_load_ok else "view load: FAIL")
    print("workspace scope: OK" if workspace_scope_ok else "workspace scope: FAIL")

    if not (view_create_ok and view_load_ok and workspace_scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
