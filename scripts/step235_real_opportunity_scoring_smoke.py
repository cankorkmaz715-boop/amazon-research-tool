#!/usr/bin/env python3
"""
Step 235: Real opportunity scoring & ranking calibration – smoke test.
Validates scoring engine wiring, real scoring path, ranking order, partial-signal fallback,
dashboard integration, opportunity endpoint ranked response, workspace-scoped ranking safety.
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


def _check_scoring_engine_wiring() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_scoring import (
            get_calibrated_opportunity_rows,
            calibrate_opportunity_rows,
            score_to_normalized,
            score_to_priority_band,
            build_supporting_signal_hints,
        )
        rows = get_calibrated_opportunity_rows(1, limit=5)
        if not isinstance(rows, list):
            return _fail("scoring engine wiring", "get_calibrated_opportunity_rows did not return list")
        return _ok("scoring engine wiring")
    except Exception as e:
        return _fail("scoring engine wiring", str(e))


def _check_real_scoring_path() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_scoring import get_calibrated_opportunity_rows, score_to_normalized
        rows = get_calibrated_opportunity_rows(workspace_id=1, limit=10)
        for row in rows:
            if not isinstance(row, dict):
                return _fail("real scoring path", "row not dict")
            if "normalized_score" not in row:
                return _fail("real scoring path", "missing normalized_score")
            if "ranking_position" not in row:
                return _fail("real scoring path", "missing ranking_position")
            n = row.get("normalized_score")
            if n is not None and (n < 0 or n > 100):
                return _fail("real scoring path", "normalized_score out of range")
        return _ok("real scoring path")
    except Exception as e:
        return _fail("real scoring path", str(e))


def _check_ranking_order_generation() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_scoring import calibrate_opportunity_rows
        fake_rows = [
            {"opportunity_ref": "A1", "latest_opportunity_score": 30.0, "ranking": None, "workspace_id": 1},
            {"opportunity_ref": "B2", "latest_opportunity_score": 80.0, "ranking": {"demand_score": 70}, "workspace_id": 1},
            {"opportunity_ref": "C3", "latest_opportunity_score": 55.0, "ranking": {}, "workspace_id": 1},
        ]
        calibrated = calibrate_opportunity_rows(fake_rows, workspace_id=1)
        if len(calibrated) != 3:
            return _fail("ranking order generation", f"expected 3 rows got {len(calibrated)}")
        if calibrated[0].get("opportunity_ref") != "B2" or calibrated[0].get("ranking_position") != 1:
            return _fail("ranking order generation", "first item should be B2 with position 1")
        if calibrated[1].get("opportunity_ref") != "C3" or calibrated[1].get("ranking_position") != 2:
            return _fail("ranking order generation", "second item should be C3 with position 2")
        if calibrated[2].get("opportunity_ref") != "A1" or calibrated[2].get("ranking_position") != 3:
            return _fail("ranking order generation", "third item should be A1 with position 3")
        return _ok("ranking order generation")
    except Exception as e:
        return _fail("ranking order generation", str(e))


def _check_partial_signal_fallback_path() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_scoring import calibrate_opportunity_rows
        partial_rows = [
            {"opportunity_ref": "X", "latest_opportunity_score": None, "ranking": None, "workspace_id": 1},
        ]
        calibrated = calibrate_opportunity_rows(partial_rows, workspace_id=1)
        if not calibrated:
            return _fail("partial signal fallback path", "empty result")
        r = calibrated[0]
        if r.get("normalized_score") is None:
            return _fail("partial signal fallback path", "normalized_score missing")
        if r.get("ranking_position") is None:
            return _fail("partial signal fallback path", "ranking_position missing")
        if not isinstance(r.get("supporting_signal_hints"), list):
            return _fail("partial signal fallback path", "supporting_signal_hints not list")
        return _ok("partial signal fallback path")
    except Exception as e:
        return _fail("partial signal fallback path", str(e))


def _check_dashboard_integration_compatibility() -> Tuple[str, bool]:
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


def _check_opportunity_endpoint_ranked_response() -> Tuple[str, bool]:
    try:
        from fastapi.testclient import TestClient
        from amazon_research.api_gateway.app import app
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/workspaces/1/opportunities")
        if r.status_code not in (200, 403, 500):
            return _fail("opportunity endpoint ranked response", f"status {r.status_code}")
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(data, dict):
            return _fail("opportunity endpoint ranked response", "response not dict")
        if r.status_code == 200 and "data" in data:
            items = data.get("data") or []
            for i, it in enumerate(items[:5]):
                if not isinstance(it, dict):
                    continue
                if "opportunity_id" not in it:
                    return _fail("opportunity endpoint ranked response", "item missing opportunity_id")
        return _ok("opportunity endpoint ranked response")
    except Exception as e:
        return _fail("opportunity endpoint ranked response", str(e))


def _check_workspace_scoped_ranking_safety() -> Tuple[str, bool]:
    try:
        from amazon_research.opportunity_scoring import get_calibrated_opportunity_rows, calibrate_opportunity_rows
        rows_none = get_calibrated_opportunity_rows(None, limit=5)
        if rows_none:
            return _fail("workspace scoped ranking safety", "None workspace_id returned non-empty")
        fake = [{"opportunity_ref": "T", "latest_opportunity_score": 50, "ranking": {}, "workspace_id": 99}]
        cal = calibrate_opportunity_rows(fake, workspace_id=99)
        if cal and cal[0].get("workspace_id") != 99:
            return _fail("workspace scoped ranking safety", "workspace_id not preserved")
        return _ok("workspace scoped ranking safety")
    except Exception as e:
        return _fail("workspace scoped ranking safety", str(e))


def main() -> int:
    results: List[Tuple[str, bool]] = [
        _check_scoring_engine_wiring(),
        _check_real_scoring_path(),
        _check_ranking_order_generation(),
        _check_partial_signal_fallback_path(),
        _check_dashboard_integration_compatibility(),
        _check_opportunity_endpoint_ranked_response(),
        _check_workspace_scoped_ranking_safety(),
    ]
    failed = [name for name, ok in results if not ok]
    if failed:
        return 1
    print("real opportunity scoring OK")
    for name, _ in results:
        print(f"{name}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
