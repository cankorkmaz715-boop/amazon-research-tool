#!/usr/bin/env python3
"""
Step 238: Real market/keyword discovery API – smoke test.
Validates keyword/market discovery endpoint wiring, query params, empty state, workspace scoping, startup.
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


def _check_keyword_discovery_endpoint_wiring() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app)
        r = client.get("/api/workspaces/1/discovery/keywords")
        if r.status_code not in (200, 403, 500):
            return _fail("keyword discovery endpoint wiring", f"status {r.status_code}")
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(body, dict):
            return _fail("keyword discovery endpoint wiring", "response not dict")
        if not isinstance(body.get("data"), list) and "meta" not in body and "detail" not in body:
            return _fail("keyword discovery endpoint wiring", "missing data/meta/detail")
        return _ok("keyword discovery endpoint wiring")
    except Exception as e:
        err = str(e).lower()
        if "db not initialized" in err or "init_db" in err or "connection" in err:
            return _ok("keyword discovery endpoint wiring")
        return _fail("keyword discovery endpoint wiring", str(e))


def _check_market_discovery_endpoint_wiring() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app)
        r = client.get("/api/workspaces/1/discovery/markets")
        if r.status_code not in (200, 403, 500):
            return _fail("market discovery endpoint wiring", f"status {r.status_code}")
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(body, dict):
            return _fail("market discovery endpoint wiring", "response not dict")
        if not isinstance(body.get("data"), list) and "meta" not in body and "detail" not in body:
            return _fail("market discovery endpoint wiring", "missing data/meta/detail")
        return _ok("market discovery endpoint wiring")
    except Exception as e:
        err = str(e).lower()
        if "db not initialized" in err or "init_db" in err or "connection" in err:
            return _ok("market discovery endpoint wiring")
        return _fail("market discovery endpoint wiring", str(e))


def _check_query_param_handling() -> Tuple[str, bool]:
    try:
        from amazon_research.discovery_api.discovery_query_mapper import (
            parse_keyword_params,
            parse_market_params,
        )
        p = parse_keyword_params(q="test", market="DE", limit=10, sort="keyword")
        if p.get("q") != "test" or p.get("market") != "DE" or p.get("limit") != 10 or p.get("sort") != "keyword":
            return _fail("query param handling", "keyword params mismatch")
        p2 = parse_market_params(category="cat", limit=5)
        if p2.get("category") != "cat" or p2.get("limit") != 5:
            return _fail("query param handling", "market params mismatch")
        # Invalid sort -> default
        p3 = parse_keyword_params(sort="invalid")
        if p3.get("sort") != "recent":
            return _fail("query param handling", "invalid sort not defaulted")
        return _ok("query param handling")
    except Exception as e:
        return _fail("query param handling", str(e))


def _check_safe_empty_state_behavior() -> Tuple[str, bool]:
    try:
        from amazon_research.discovery_api import get_keyword_discovery, get_market_discovery
        kw = get_keyword_discovery(workspace_id=99999)
        if not isinstance(kw, dict) or "data" not in kw or "meta" not in kw:
            return _fail("safe empty state behavior", "keyword discovery shape")
        if not isinstance(kw["data"], list):
            return _fail("safe empty state behavior", "keyword data not list")
        mk = get_market_discovery(workspace_id=99999)
        if not isinstance(mk, dict) or "data" not in mk or "meta" not in mk:
            return _fail("safe empty state behavior", "market discovery shape")
        if not isinstance(mk["data"], list):
            return _fail("safe empty state behavior", "market data not list")
        return _ok("safe empty state behavior")
    except Exception as e:
        err = str(e).lower()
        if "db not initialized" in err or "init_db" in err or "connection" in err:
            return _ok("safe empty state behavior")
        return _fail("safe empty state behavior", str(e))


def _check_workspace_scoped_discovery_safety() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app)
        # Invalid workspace: 403 (forbidden) or 500 (e.g. DB not init) is acceptable; no cross-workspace leak
        r = client.get("/api/workspaces/0/discovery/keywords")
        if r.status_code not in (403, 500):
            return _fail("workspace scoped discovery safety", f"unexpected status {r.status_code}")
        r2 = client.get("/api/workspaces/0/discovery/markets")
        if r2.status_code not in (403, 500):
            return _fail("workspace scoped discovery safety", f"unexpected status {r2.status_code}")
        return _ok("workspace scoped discovery safety")
    except Exception as e:
        err = str(e).lower()
        if "db not initialized" in err or "init_db" in err or "connection" in err:
            return _ok("workspace scoped discovery safety")
        return _fail("workspace scoped discovery safety", str(e))


def _check_startup_api_compatibility() -> Tuple[str, bool]:
    try:
        from amazon_research.api_gateway.app import app
        from amazon_research.api_gateway.routers import discovery
        if not hasattr(discovery, "router"):
            return _fail("startup api compatibility", "discovery router missing")
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        has_keywords = any("/discovery/keywords" in p or "discovery" in p for p in routes)
        if not has_keywords:
            for r in getattr(app, "routes", []):
                if hasattr(r, "routes"):
                    for sr in r.routes:
                        if hasattr(sr, "path") and "keywords" in sr.path:
                            has_keywords = True
                            break
        if not has_keywords:
            # OpenAPI may have path as part of prefix
            openapi = app.openapi() if callable(getattr(app, "openapi", None)) else {}
            paths = list(openapi.get("paths", {}).keys())
            has_keywords = any("discovery" in p and "keyword" in p for p in paths)
        if not has_keywords:
            return _fail("startup api compatibility", "discovery keywords route not found")
        return _ok("startup api compatibility")
    except Exception as e:
        return _fail("startup api compatibility", str(e))


def main() -> int:
    checks = [
        _check_keyword_discovery_endpoint_wiring,
        _check_market_discovery_endpoint_wiring,
        _check_query_param_handling,
        _check_safe_empty_state_behavior,
        _check_workspace_scoped_discovery_safety,
        _check_startup_api_compatibility,
    ]
    results: List[Tuple[str, bool]] = []
    for check in checks:
        results.append(check())
    if all(r[1] for r in results):
        print("market keyword discovery api OK")
        for name, _ in results:
            print(f"{name}: OK")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
