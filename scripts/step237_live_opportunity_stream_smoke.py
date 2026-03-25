#!/usr/bin/env python3
"""
Step 237: Live opportunity stream & runtime feed refresh – smoke test.
Validates live stream wiring, new opportunity refresh path, existing update path,
no-change no-op path, persisted feed freshness, dashboard/API compatibility, workspace-scoped safety.
"""
from pathlib import Path
import sys
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent


def _ok(name: str) -> Tuple[str, bool]:
    return (name, True)


def _fail(name: str, msg: str) -> Tuple[str, bool]:
    print(f"{name}: FAIL — {msg}", file=sys.stderr)
    return (name, False)


def _check_live_stream_wiring() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_stream import (
            run_live_feed_refresh_cycle,
            run_feed_refresh_for_workspace,
            run_feed_refresh_cycle,
            CYCLE_OPPORTUNITY_FEED_REFRESH,
        )
        from amazon_research.scheduler.production_loop import (
            CYCLE_OPPORTUNITY_FEED_REFRESH as CYCLE_NAME,
            DEFAULT_INTERVALS,
            _CYCLE_RUNNERS,
        )
        if CYCLE_NAME not in DEFAULT_INTERVALS or CYCLE_NAME not in _CYCLE_RUNNERS:
            return _fail("live stream wiring", "cycle not registered in production loop")
        return _ok("live stream wiring")
    except Exception as e:
        return _fail("live stream wiring", str(e))


def _check_new_opportunity_refresh_path() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_stream import run_feed_refresh_for_workspace
        # Refresh for workspace (may have 0 or more opportunities; no crash)
        res = run_feed_refresh_for_workspace(1)
        if not isinstance(res, dict):
            return _fail("new opportunity refresh path", "expected dict")
        if "workspace_id" not in res and "opportunity_count" not in res:
            return _fail("new opportunity refresh path", "missing keys")
        return _ok("new opportunity refresh path")
    except Exception as e:
        return _fail("new opportunity refresh path", str(e))


def _check_existing_opportunity_update_path() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_stream import run_feed_refresh_for_workspace
        # Second refresh for same workspace = update path (idempotent / no-op or update)
        res1 = run_feed_refresh_for_workspace(1)
        res2 = run_feed_refresh_for_workspace(1)
        if not isinstance(res1, dict) or not isinstance(res2, dict):
            return _fail("existing opportunity update path", "expected dict")
        return _ok("existing opportunity update path")
    except Exception as e:
        return _fail("existing opportunity update path", str(e))


def _check_no_change_no_op_path() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_stream import run_feed_refresh_cycle
        # Run cycle (may be no workspaces = no-op)
        results = run_feed_refresh_cycle()
        if not isinstance(results, list):
            return _fail("no change no op path", "expected list")
        return _ok("no change no op path")
    except Exception as e:
        return _fail("no change no op path", str(e))


def _check_persisted_feed_freshness_path() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_feed.opportunity_feed_service import get_real_opportunity_feed
        from amazon_research.opportunity_persistence import get_feed_from_persistence
        # After refresh, persisted feed can be read (or empty)
        items = get_feed_from_persistence(1, limit=20)
        if not isinstance(items, list):
            return _fail("persisted feed freshness path", "expected list")
        # Feed service with prefer_persisted=True returns from persistence when available
        feed_items, _ = get_real_opportunity_feed(1, limit=20, prefer_persisted=True)
        if not isinstance(feed_items, list):
            return _fail("persisted feed freshness path", "feed not list")
        return _ok("persisted feed freshness path")
    except Exception as e:
        return _fail("persisted feed freshness path", str(e))


def _check_dashboard_api_compatibility() -> Tuple[str, bool]:
    try:
        from amazon_research.dashboard_serving.aggregation import get_dashboard_payload
        payload = get_dashboard_payload(1)
        if not isinstance(payload, dict):
            return _fail("dashboard api compatibility", "payload not dict")
        top = (payload.get("top_items") or {}).get("top_opportunities") or []
        if not isinstance(top, list):
            return _fail("dashboard api compatibility", "top_opportunities not list")
        return _ok("dashboard api compatibility")
    except Exception as e:
        return _fail("dashboard api compatibility", str(e))


def _check_workspace_scoped_refresh_safety() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_stream.opportunity_refresh_runner import run_feed_refresh_for_workspace
        # Invalid workspace_id: should not crash; returns result with error or count 0
        res = run_feed_refresh_for_workspace(0)
        if not isinstance(res, dict):
            return _fail("workspace scoped refresh safety", "expected dict")
        # Cycle only processes workspaces from list_workspaces (no cross-workspace)
        from amazon_research.opportunity_stream import run_feed_refresh_cycle
        results = run_feed_refresh_cycle()
        for r in results:
            if not isinstance(r, dict) or "workspace_id" not in r:
                return _fail("workspace scoped refresh safety", "result missing workspace_id")
        return _ok("workspace scoped refresh safety")
    except Exception as e:
        return _fail("workspace scoped refresh safety", str(e))


def main() -> int:
    results: List[Tuple[str, bool]] = [
        _check_live_stream_wiring(),
        _check_new_opportunity_refresh_path(),
        _check_existing_opportunity_update_path(),
        _check_no_change_no_op_path(),
        _check_persisted_feed_freshness_path(),
        _check_dashboard_api_compatibility(),
        _check_workspace_scoped_refresh_safety(),
    ]
    failed = [name for name, ok in results if not ok]
    if failed:
        return 1
    print("live opportunity stream OK")
    for name, _ in results:
        print(f"{name}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
