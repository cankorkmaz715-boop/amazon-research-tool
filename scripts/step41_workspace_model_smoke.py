#!/usr/bin/env python3
"""Step 41: User / Workspace model v1 – workspace create, user link, workspace scoping."""
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
        get_workspace,
        list_workspaces,
        create_user,
        get_users_for_workspace,
        upsert_asin,
        list_asins_by_workspace,
    )

    init_db()

    # Apply 005 workspace/user schema
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON workspaces(slug)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                identifier TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(workspace_id, identifier)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_workspace_id ON users(workspace_id)")
        cur.execute("ALTER TABLE asins ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_asins_workspace_id ON asins(workspace_id)")
        cur.execute("ALTER TABLE discovery_seeds ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_discovery_seeds_workspace_id ON discovery_seeds(workspace_id)")
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema ensure failed: {e}") from e

    # Workspace create
    wid = create_workspace("Step41 Test Workspace", "step41-test")
    ws = get_workspace(wid)
    workspace_ok = ws is not None and ws.get("slug") == "step41-test" and len(list_workspaces()) >= 1

    # User link
    uid = create_user(wid, "step41-user@test")
    users = get_users_for_workspace(wid)
    user_link_ok = uid is not None and len(users) >= 1 and any(u.get("identifier") == "step41-user@test" for u in users)

    # Workspace scoping: asin with workspace_id, then list by workspace
    upsert_asin("WS41ASIN001", title="Scoped ASIN", workspace_id=wid)
    scoped = list_asins_by_workspace(wid)
    scope_ok = len(scoped) >= 1 and any(a.get("asin") == "WS41ASIN001" and a.get("workspace_id") == wid for a in scoped)

    print("workspace model v1 OK")
    print("workspace create: OK" if workspace_ok else "workspace create: FAIL")
    print("user link: OK" if user_link_ok else "user link: FAIL")
    print("workspace scoping: OK" if scope_ok else "workspace scoping: FAIL")

    if not (workspace_ok and user_link_ok and scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
