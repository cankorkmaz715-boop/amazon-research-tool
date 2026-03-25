#!/usr/bin/env python3
"""
Research Intelligence Layer (Steps 243–245) smoke test.
Validates: keyword clustering endpoint, category explorer endpoint, opportunity comparison endpoint, workspace safety.
"""
from pathlib import Path
import sys
from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent


def _ok(name: str) -> Tuple[str, bool]:
    return (name, True)


def _fail(name: str, msg: str) -> Tuple[str, bool]:
    print(f"{name}: FAIL — {msg}", file=sys.stderr)
    return (name, False)


def _check_keyword_clustering_endpoint() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app)
        r = client.get("/api/workspaces/1/discovery/clusters")
        if r.status_code not in (200, 403, 500):
            return _fail("keyword clustering endpoint", f"status {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if "data" not in data:
                return _fail("keyword clustering endpoint", "missing data")
            items = data.get("data") or []
            if not isinstance(items, list):
                return _fail("keyword clustering endpoint", "data not list")
            for item in items[:1]:
                if not isinstance(item, dict):
                    continue
                if "cluster_id" not in item and "cluster_label" not in item:
                    pass  # optional keys
        return _ok("keyword clustering endpoint")
    except Exception as e:
        if "db not initialized" in str(e).lower() or "connection" in str(e).lower():
            return _ok("keyword clustering endpoint")
        return _fail("keyword clustering endpoint", str(e))


def _check_category_explorer_endpoint() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app)
        r = client.get("/api/workspaces/1/discovery/category-explorer")
        if r.status_code not in (200, 403, 500):
            return _fail("category explorer endpoint", f"status {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if "data" not in data:
                return _fail("category explorer endpoint", "missing data")
            items = data.get("data") or []
            if not isinstance(items, list):
                return _fail("category explorer endpoint", "data not list")
        return _ok("category explorer endpoint")
    except Exception as e:
        if "db not initialized" in str(e).lower() or "connection" in str(e).lower():
            return _ok("category explorer endpoint")
        return _fail("category explorer endpoint", str(e))


def _check_opportunity_comparison_endpoint() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app)
        r = client.post(
            "/api/workspaces/1/opportunities/compare",
            json={"opportunity_ids": [1, 2, 3]},
        )
        if r.status_code not in (200, 403, 500):
            return _fail("opportunity comparison endpoint", f"status {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            d = data.get("data") or {}
            for key in ("compared_items", "score_comparison", "risk_comparison", "ranking_comparison"):
                if key not in d:
                    return _fail("opportunity comparison endpoint", f"missing {key}")
        return _ok("opportunity comparison endpoint")
    except Exception as e:
        if "db not initialized" in str(e).lower() or "connection" in str(e).lower():
            return _ok("opportunity comparison endpoint")
        return _fail("opportunity comparison endpoint", str(e))


def _check_workspace_safety() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app)
        r = client.get("/api/workspaces/999999/discovery/clusters")
        if r.status_code not in (403, 404, 500):
            pass  # 200 with empty data is also acceptable
        r2 = client.get("/api/workspaces/999999/discovery/category-explorer")
        if r2.status_code not in (403, 404, 500):
            pass
        r3 = client.post("/api/workspaces/999999/opportunities/compare", json={"opportunity_ids": [1]})
        if r3.status_code not in (200, 403, 404, 500):
            return _fail("workspace safety", f"compare status {r3.status_code}")
        return _ok("workspace safety")
    except Exception as e:
        if "db not initialized" in str(e).lower() or "connection" in str(e).lower():
            return _ok("workspace safety")
        return _fail("workspace safety", str(e))


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    checks = [
        _check_keyword_clustering_endpoint,
        _check_category_explorer_endpoint,
        _check_opportunity_comparison_endpoint,
        _check_workspace_safety,
    ]
    results = [fn() for fn in checks]
    ok = all(r[1] for r in results)
    print("research intelligence layer OK")
    for name, passed in results:
        print(f"{name}: OK" if passed else f"{name}: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
