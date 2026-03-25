#!/usr/bin/env python3
"""
Step 234: Real opportunity feed engine – smoke test.
Validates feed engine wiring, real load path, demo fallback path, dashboard integration,
opportunity endpoint compatibility, and workspace-scoped response safety.
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


def _check_feed_engine_wiring() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_feed import (
            get_real_opportunity_feed,
            get_opportunity_feed_for_dashboard,
            SOURCE_REAL,
            SOURCE_DEMO,
        )
        items, is_real = get_real_opportunity_feed(1, limit=5)
        if not isinstance(items, list):
            return _fail("feed engine wiring", "get_real_opportunity_feed did not return list")
        if not isinstance(is_real, bool):
            return _fail("feed engine wiring", "is_real not bool")
        return _ok("feed engine wiring")
    except Exception as e:
        return _fail("feed engine wiring", str(e))


def _check_real_opportunity_load_path() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_feed import get_real_opportunity_feed
        items, _ = get_real_opportunity_feed(workspace_id=1, limit=10)
        for item in items:
            if not isinstance(item, dict):
                return _fail("real opportunity load path", "item not dict")
            if "opportunity_id" not in item:
                return _fail("real opportunity load path", "missing opportunity_id")
            if item.get("source_type") != "real":
                return _fail("real opportunity load path", "source_type not real")
        return _ok("real opportunity load path")
    except Exception as e:
        return _fail("real opportunity load path", str(e))


def _check_demo_fallback_path() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_feed import get_real_opportunity_feed
        from amazon_research.demo_data import should_use_demo_for_dashboard
        empty_payload = {
            "overview": {"total_opportunities": 0, "total_portfolio_items": 0},
            "top_items": {"top_opportunities": []},
            "portfolio_summary": {"total": 0},
        }
        items, is_real = get_real_opportunity_feed(workspace_id=99999, limit=5)
        if not isinstance(items, list):
            return _fail("demo fallback path", "items not list")
        use_demo = should_use_demo_for_dashboard(99999, empty_payload)
        if not isinstance(use_demo, bool):
            return _fail("demo fallback path", "should_use_demo not bool")
        return _ok("demo fallback path")
    except Exception as e:
        return _fail("demo fallback path", str(e))


def _check_dashboard_integration() -> Tuple[str, bool]:
    try:
        from amazon_research.dashboard_serving.aggregation import get_dashboard_payload
        payload = get_dashboard_payload(1)
        if not isinstance(payload, dict):
            return _fail("dashboard integration compatibility", "payload not dict")
        top = (payload.get("top_items") or {}).get("top_opportunities") or []
        if not isinstance(top, list):
            return _fail("dashboard integration compatibility", "top_opportunities not list")
        for item in top[:3]:
            if not isinstance(item, dict):
                return _fail("dashboard integration compatibility", "item not dict")
            if "opportunity_id" not in item:
                return _fail("dashboard integration compatibility", "missing opportunity_id")
        return _ok("dashboard integration compatibility")
    except Exception as e:
        return _fail("dashboard integration compatibility", str(e))


def _check_opportunity_endpoint_compatibility() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/workspaces/1/opportunities")
        if r.status_code not in (200, 403, 500):
            return _fail("opportunity endpoint compatibility", f"status {r.status_code}")
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(data, dict):
            return _fail("opportunity endpoint compatibility", "response not dict")
        if r.status_code == 200 and "data" in data:
            if not isinstance(data["data"], list):
                return _fail("opportunity endpoint compatibility", "data not list")
            if "meta" in data and "workspace_id" not in data.get("meta", {}):
                return _fail("opportunity endpoint compatibility", "meta.workspace_id missing")
        return _ok("opportunity endpoint compatibility")
    except Exception as e:
        return _fail("opportunity endpoint compatibility", str(e))


def _check_workspace_scoped_response_safety() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_feed.opportunity_feed_repository import list_real_opportunities_for_workspace
        rows_none = list_real_opportunities_for_workspace(None, limit=5)
        if rows_none:
            return _fail("workspace scoped response safety", "None workspace_id returned non-empty")
        rows_1 = list_real_opportunities_for_workspace(1, limit=5)
        for r in rows_1:
            if r.get("workspace_id") != 1:
                return _fail("workspace scoped response safety", "workspace_id mismatch in row")
        return _ok("workspace scoped response safety")
    except Exception as e:
        return _fail("workspace scoped response safety", str(e))


def main() -> int:
    results: List[Tuple[str, bool]] = [
        _check_feed_engine_wiring(),
        _check_real_opportunity_load_path(),
        _check_demo_fallback_path(),
        _check_dashboard_integration(),
        _check_opportunity_endpoint_compatibility(),
        _check_workspace_scoped_response_safety(),
    ]
    failed = [name for name, ok in results if not ok]
    if failed:
        return 1
    print("real opportunity feed engine OK")
    for name, _ in results:
        print(f"{name}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
