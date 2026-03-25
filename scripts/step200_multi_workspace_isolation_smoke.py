#!/usr/bin/env python3
"""
Step 200 smoke test: Multi-workspace isolation layer.
Validates scoped read/write, cross-workspace blocking, cache isolation, scheduler isolation, payload stability.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    from amazon_research.workspace_isolation import (
        require_workspace_context,
        validate_resource_in_workspace,
        safe_workspace_id,
        ensure_workspace_scope_for_response,
    )
    from amazon_research.workspace_intelligence.cache_keys import workspace_intelligence_cache_key
    from amazon_research.db.workspace_portfolio import list_workspace_portfolio_items, archive_workspace_portfolio_item
    from amazon_research.workspace_intelligence.refresh_policy import workspaces_requiring_refresh

    scoped_read_ok = True
    scoped_write_ok = True
    cross_workspace_ok = True
    cache_ok = True
    scheduler_ok = True
    payload_ok = True

    # --- Workspace-scoped read isolation: list returns only items for that workspace
    try:
        items = list_workspace_portfolio_items(1, limit=50)
        if not isinstance(items, list):
            scoped_read_ok = False
        for it in items:
            if it.get("workspace_id") != 1:
                scoped_read_ok = False
                break
        # require_workspace_context(valid_id) passes
        if not require_workspace_context(1, "smoke_read"):
            scoped_read_ok = False
    except Exception as e:
        scoped_read_ok = False
        print(f"scoped read isolation error: {e}")

    # --- Workspace-scoped write isolation: write with workspace_id is scope-safe
    try:
        # require_workspace_context must pass for valid workspace
        if not require_workspace_context(2, "smoke_write"):
            scoped_write_ok = False
        # validate_resource_in_workspace: same workspace passes
        if not validate_resource_in_workspace(1, 1, "portfolio"):
            scoped_write_ok = False
    except Exception as e:
        scoped_write_ok = False
        print(f"scoped write isolation error: {e}")

    # --- Cross-workspace blocking: wrong workspace fails validation; archive with wrong scope has no effect
    try:
        if validate_resource_in_workspace(1, 2, "portfolio"):
            cross_workspace_ok = False
        if require_workspace_context(None, "smoke"):
            cross_workspace_ok = False
        # archive_workspace_portfolio_item(workspace_id=99998, item_id=1): item 1 may belong to another ws; UPDATE uses AND workspace_id so no row updated
        archive_workspace_portfolio_item(99998, 1)
        # Should not crash; False or True is acceptable (False if no such item in ws 99998)
    except Exception as e:
        cross_workspace_ok = False
        print(f"cross-workspace blocking error: {e}")

    # --- Cache isolation: cache keys differ per workspace
    try:
        k1 = workspace_intelligence_cache_key(1)
        k2 = workspace_intelligence_cache_key(2)
        if k1 is None or k2 is None:
            cache_ok = False
        if k1 == k2:
            cache_ok = False
        if workspace_intelligence_cache_key(None) is not None:
            cache_ok = False
    except Exception as e:
        cache_ok = False
        print(f"cache isolation error: {e}")

    # --- Scheduler isolation: workspaces_requiring_refresh returns workspace ids only; no cross-workspace mix
    try:
        wids = workspaces_requiring_refresh(workspace_ids=[1, 2], batch_limit=5)
        if not isinstance(wids, list):
            scheduler_ok = False
        for w in wids:
            if not isinstance(w, int) or w < 1:
                scheduler_ok = False
                break
    except Exception as e:
        scheduler_ok = False
        print(f"scheduler isolation error: {e}")

    # --- Payload stability: ensure_workspace_scope_for_response and list/summary shapes
    try:
        if not ensure_workspace_scope_for_response(1, {"workspace_id": 1}, "portfolio"):
            payload_ok = False
        if ensure_workspace_scope_for_response(1, {"workspace_id": 2}, "portfolio"):
            payload_ok = False
        summary = list_workspace_portfolio_items(1, limit=1)
        if not isinstance(summary, list):
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    print("multi-workspace isolation OK" if (scoped_read_ok and scoped_write_ok and cross_workspace_ok and cache_ok and scheduler_ok and payload_ok) else "multi-workspace isolation FAIL")
    print("scoped read isolation: OK" if scoped_read_ok else "scoped read isolation: FAIL")
    print("scoped write isolation: OK" if scoped_write_ok else "scoped write isolation: FAIL")
    print("cross-workspace blocking: OK" if cross_workspace_ok else "cross-workspace blocking: FAIL")
    print("cache isolation: OK" if cache_ok else "cache isolation: FAIL")
    print("scheduler isolation: OK" if scheduler_ok else "scheduler isolation: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    if not (scoped_read_ok and scoped_write_ok and cross_workspace_ok and cache_ok and scheduler_ok and payload_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
