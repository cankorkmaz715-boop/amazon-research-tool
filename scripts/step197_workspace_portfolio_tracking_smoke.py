#!/usr/bin/env python3
"""
Step 197 smoke test: Workspace portfolio tracking layer.
Validates add, deduplication, list, archive, summary stability, empty portfolio resilience.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

SUMMARY_KEYS = {"workspace_id", "total", "by_type", "by_status"}
ITEM_KEYS = {"id", "workspace_id", "item_type", "item_key", "item_label", "source_type", "metadata_json", "status", "created_at", "updated_at"}


def main() -> None:
    from amazon_research.db.workspace_portfolio import (
        add_workspace_portfolio_item,
        list_workspace_portfolio_items,
        archive_workspace_portfolio_item,
        get_workspace_portfolio_summary,
    )

    add_ok = True
    dedup_ok = True
    list_ok = True
    archive_ok = True
    summary_ok = True
    empty_ok = True

    # --- Portfolio add: returns { id, created }; no crash on missing DB
    try:
        r = add_workspace_portfolio_item(99992, "asin", "B001TEST01", item_label="Test ASIN")
        if not isinstance(r, dict) or "id" not in r or "created" not in r:
            add_ok = False
    except Exception as e:
        add_ok = False
        print(f"portfolio add error: {e}")

    # --- Portfolio deduplication: second add same (workspace, type, key) returns created=False
    try:
        r1 = add_workspace_portfolio_item(99992, "asin", "B001DEDUP01")
        r2 = add_workspace_portfolio_item(99992, "asin", "B001DEDUP01")
        if not isinstance(r2, dict) or r2.get("created") is not False:
            dedup_ok = False
    except Exception as e:
        dedup_ok = False
        print(f"portfolio deduplication error: {e}")

    # --- Portfolio listing: returns list of items with stable shape
    try:
        items = list_workspace_portfolio_items(99992, limit=10)
        if not isinstance(items, list):
            list_ok = False
        for it in items:
            if not isinstance(it, dict) or not ITEM_KEYS.issubset(it.keys()):
                list_ok = False
                break
    except Exception as e:
        list_ok = False
        print(f"portfolio listing error: {e}")

    # --- Portfolio archive: archive_workspace_portfolio_item returns bool
    try:
        items = list_workspace_portfolio_items(99992, status="active", limit=1)
        if items:
            item_id = items[0]["id"]
            ok = archive_workspace_portfolio_item(99992, item_id)
            if not isinstance(ok, bool):
                archive_ok = False
        # If no items, archive(99992, 0) returns False without crash
        archive_workspace_portfolio_item(99992, 0)
    except Exception as e:
        archive_ok = False
        print(f"portfolio archive error: {e}")

    # --- Portfolio summary stability: get_workspace_portfolio_summary returns stable shape
    try:
        s = get_workspace_portfolio_summary(99992)
        if not isinstance(s, dict) or not SUMMARY_KEYS.issubset(s.keys()):
            summary_ok = False
        if not isinstance(s.get("by_status"), dict) or "active" not in s["by_status"] or "archived" not in s["by_status"]:
            summary_ok = False
    except Exception as e:
        summary_ok = False
        print(f"portfolio summary stability error: {e}")

    # --- Empty portfolio resilience: list/summary for workspace with no items (or no DB) don't crash
    try:
        empty_list = list_workspace_portfolio_items(99999, limit=5)
        empty_summary = get_workspace_portfolio_summary(99999)
        if not isinstance(empty_list, list):
            empty_ok = False
        if not isinstance(empty_summary, dict) or not SUMMARY_KEYS.issubset(empty_summary.keys()):
            empty_ok = False
        if empty_summary.get("total", -1) < 0:
            empty_ok = False
    except Exception as e:
        empty_ok = False
        print(f"empty portfolio resilience error: {e}")

    print("workspace portfolio tracking OK" if (add_ok and dedup_ok and list_ok and archive_ok and summary_ok and empty_ok) else "workspace portfolio tracking FAIL")
    print("portfolio add: OK" if add_ok else "portfolio add: FAIL")
    print("portfolio deduplication: OK" if dedup_ok else "portfolio deduplication: FAIL")
    print("portfolio listing: OK" if list_ok else "portfolio listing: FAIL")
    print("portfolio archive: OK" if archive_ok else "portfolio archive: FAIL")
    print("portfolio summary stability: OK" if summary_ok else "portfolio summary stability: FAIL")
    print("empty portfolio resilience: OK" if empty_ok else "empty portfolio resilience: FAIL")
    if not (add_ok and dedup_ok and list_ok and archive_ok and summary_ok and empty_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
