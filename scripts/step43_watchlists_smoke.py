#!/usr/bin/env python3
"""Step 43: Opportunity watchlists – workspace-scoped ASIN watchlists."""
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
        upsert_asin,
        get_asin_id,
        create_watchlist,
        get_watchlist,
        list_watchlists,
        add_watchlist_item,
        remove_watchlist_item,
        list_watchlist_items,
    )

    init_db()

    # Ensure workspaces and watchlists tables exist
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
            CREATE TABLE IF NOT EXISTS watchlists (
                id SERIAL PRIMARY KEY,
                workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_items (
                id SERIAL PRIMARY KEY,
                watchlist_id INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
                asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(watchlist_id, asin_id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_watchlists_workspace_id ON watchlists(workspace_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist_id ON watchlist_items(watchlist_id)")
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema ensure failed: {e}") from e

    wid = create_workspace("Step43 Watchlist Test", "step43-watch")
    other_wid = create_workspace("Other WS", "step43-other")

    # Watchlist create
    wl_id = create_watchlist(wid, "High opportunity")
    wl = get_watchlist(wl_id)
    watchlist_create_ok = wl_id is not None and wl is not None and wl.get("name") == "High opportunity"

    # Item add/remove: add two ASINs, remove one
    id_a = upsert_asin("W43ASIN001", title="Watch A")
    id_b = upsert_asin("W43ASIN002", title="Watch B")
    add_ok_1 = add_watchlist_item(wl_id, id_a)
    add_ok_2 = add_watchlist_item(wl_id, id_b)
    add_dup = add_watchlist_item(wl_id, id_a)
    items_before = list_watchlist_items(wl_id)
    remove_ok = remove_watchlist_item(wl_id, id_a)
    items_after = list_watchlist_items(wl_id)
    item_ok = add_ok_1 and add_ok_2 and not add_dup and len(items_before) == 2 and remove_ok and len(items_after) == 1

    # Workspace scope: watchlist in wid; list for wid returns it, list for other_wid does not
    in_workspace = list_watchlists(wid)
    in_other = list_watchlists(other_wid)
    workspace_scope_ok = len(in_workspace) >= 1 and any(w["id"] == wl_id for w in in_workspace) and not any(w["id"] == wl_id for w in in_other)

    print("watchlists OK")
    print("watchlist create: OK" if watchlist_create_ok else "watchlist create: FAIL")
    print("item add/remove: OK" if item_ok else "item add/remove: FAIL")
    print("workspace scope: OK" if workspace_scope_ok else "workspace scope: FAIL")

    if not (watchlist_create_ok and item_ok and workspace_scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
