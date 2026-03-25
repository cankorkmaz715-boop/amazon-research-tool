#!/usr/bin/env python3
"""Step 52: Workspace isolation – scoped reads/writes, cross-workspace blocked, missing workspace rejected."""
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
        create_workspace,
        create_saved_view,
        get_saved_view,
        list_saved_views,
        get_watchlist,
        create_watchlist,
        get_workspace,
    )
    from amazon_research.api import (
        get_products,
        get_metrics,
        get_scores,
        get_saved_views,
        get_watchlists,
        get_watchlist_items,
    )
    from amazon_research.export import get_research_data_for_workspace, export_research_csv

    init_db()

    ws1 = create_workspace("Isolation WS 1", slug="step52-ws1")
    ws2 = create_workspace("Isolation WS 2", slug="step52-ws2")

    # Scoped reads: handlers return error envelope when workspace_id is None
    r_products_none = get_products(limit=5, workspace_id=None)
    r_metrics_none = get_metrics(limit=5, workspace_id=None)
    r_scores_none = get_scores(limit=5, workspace_id=None)
    scoped_reads_ok = (
        r_products_none.get("error") == "workspace_id required"
        and r_metrics_none.get("error") == "workspace_id required"
        and r_scores_none.get("error") == "workspace_id required"
    )
    r_products_ws = get_products(limit=5, workspace_id=ws1)
    scoped_reads_ok = scoped_reads_ok and "data" in r_products_ws and "meta" in r_products_ws and "error" not in r_products_ws

    # Scoped writes: create_saved_view requires workspace_id; export requires workspace_id
    view_id = create_saved_view(ws1, "View A", {"sort_by": "created_at"})
    list_ok = list_saved_views(ws1)
    scoped_writes_ok = view_id and len(list_ok) >= 1
    try:
        get_research_data_for_workspace(None)
        scoped_writes_ok = False
    except ValueError as e:
        scoped_writes_ok = scoped_writes_ok and "workspace_id" in str(e)
    try:
        list_saved_views(None)
        scoped_writes_ok = False
    except ValueError as e:
        scoped_writes_ok = scoped_writes_ok and "workspace_id" in str(e)

    # Cross-workspace access blocked: get_saved_view(view_id, workspace_id=ws2) returns None
    view_in_ws1 = get_saved_view(view_id, workspace_id=ws1)
    view_in_ws2 = get_saved_view(view_id, workspace_id=ws2)
    cross_blocked_ok = view_in_ws1 is not None and view_in_ws2 is None
    wl_id = create_watchlist(ws1, "WL1")
    wl_other = get_watchlist(wl_id, workspace_id=ws2)
    cross_blocked_ok = cross_blocked_ok and wl_other is None
    r_items_wrong_ws = get_watchlist_items(watchlist_id=wl_id, workspace_id=ws2)
    cross_blocked_ok = cross_blocked_ok and r_items_wrong_ws.get("error") == "watchlist not in workspace"

    # Missing workspace rejected: API handlers and export raise or return error
    missing_ok = (
        get_saved_views(workspace_id=None).get("error") == "workspace_id required"
        and get_watchlists(workspace_id=None).get("error") == "workspace_id required"
    )
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=True) as f:
        try:
            export_research_csv(None, f.name)
            missing_ok = False
        except ValueError as e:
            missing_ok = missing_ok and "workspace_id" in str(e)

    print("workspace isolation OK")
    print("scoped reads: OK" if scoped_reads_ok else "scoped reads: FAIL")
    print("scoped writes: OK" if scoped_writes_ok else "scoped writes: FAIL")
    print("cross-workspace access blocked: OK" if cross_blocked_ok else "cross-workspace access blocked: FAIL")
    print("missing workspace rejected: OK" if missing_ok else "missing workspace rejected: FAIL")

    if not (scoped_reads_ok and scoped_writes_ok and cross_blocked_ok and missing_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
