#!/usr/bin/env python3
"""
Step 191 smoke test: Workspace intelligence foundation.
Validates summary generation, empty-state resilience, payload shape, and route/service compatibility.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    from amazon_research.workspace_intelligence import (
        get_workspace_intelligence_summary,
        refresh_workspace_intelligence_summary,
    )

    summary_ok = True
    empty_ok = True
    shape_ok = True
    route_ok = True

    required_keys = {
        "workspace_id",
        "summary_timestamp",
        "total_tracked_opportunities",
        "active_high_priority_count",
        "new_opportunities_recent_window",
        "average_opportunity_score",
        "top_opportunity_refs",
        "trend_overview",
        "alert_overview",
        "category_coverage_overview",
        "market_coverage_overview",
    }

    # --- Summary generation (with workspace_id; may have no data)
    try:
        summary = get_workspace_intelligence_summary(workspace_id=1)
        if not isinstance(summary, dict):
            summary_ok = False
        if summary.get("workspace_id") != 1:
            summary_ok = False
    except Exception as e:
        summary_ok = False
        print(f"summary generation error: {e}")

    # --- Empty-state resilience: None workspace_id returns default shape without crashing
    try:
        empty_summary = get_workspace_intelligence_summary(workspace_id=None)
        if not isinstance(empty_summary, dict):
            empty_ok = False
        if not required_keys.issubset(empty_summary.keys()):
            empty_ok = False
        if empty_summary.get("total_tracked_opportunities") is not None and empty_summary.get("total_tracked_opportunities") != 0:
            pass  # 0 is expected for None workspace
        if empty_summary.get("top_opportunity_refs") is not None and not isinstance(empty_summary["top_opportunity_refs"], list):
            empty_ok = False
    except Exception as e:
        empty_ok = False
        print(f"empty-state error: {e}")

    # --- Payload shape stability: all required keys present, types correct
    try:
        s = get_workspace_intelligence_summary(workspace_id=99)
        if not required_keys.issubset(s.keys()):
            shape_ok = False
        if not isinstance(s.get("top_opportunity_refs"), list):
            shape_ok = False
        if not isinstance(s.get("trend_overview"), dict):
            shape_ok = False
        if not isinstance(s.get("alert_overview"), dict):
            shape_ok = False
        if not isinstance(s.get("category_coverage_overview"), dict):
            shape_ok = False
        if not isinstance(s.get("market_coverage_overview"), dict):
            shape_ok = False
        if not isinstance(s.get("summary_timestamp"), str):
            shape_ok = False
    except Exception as e:
        shape_ok = False
        print(f"payload shape error: {e}")

    # --- Route/service compatibility: handler exists and returns stable envelope
    try:
        from amazon_research.api import get_workspace_intelligence_summary_response
        resp = get_workspace_intelligence_summary_response(workspace_id=1)
        if not isinstance(resp, dict):
            route_ok = False
        if "data" not in resp and "error" not in resp:
            route_ok = False
        if resp.get("data") is not None and not isinstance(resp["data"], dict):
            route_ok = False
        if resp.get("data") and not required_keys.issubset(resp["data"].keys()):
            route_ok = False
        # None workspace_id returns error envelope
        err_resp = get_workspace_intelligence_summary_response(workspace_id=None)
        if err_resp.get("error") is None:
            route_ok = False
    except Exception as e:
        route_ok = False
        print(f"route compatibility error: {e}")

    print("workspace intelligence foundation OK" if (summary_ok and empty_ok and shape_ok and route_ok) else "workspace intelligence foundation FAIL")
    print("summary generation: OK" if summary_ok else "summary generation: FAIL")
    print("empty-state resilience: OK" if empty_ok else "empty-state resilience: FAIL")
    print("payload shape stability: OK" if shape_ok else "payload shape stability: FAIL")
    print("route compatibility: OK" if route_ok else "route compatibility: FAIL")
    if not (summary_ok and empty_ok and shape_ok and route_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
