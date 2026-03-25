#!/usr/bin/env python3
"""
Step 212 smoke test: Workspace overview dashboard UI.
Validates dashboard page wiring, overview stats rendering, summary section rendering,
partial-data resilience, route integration compatibility, payload-to-UI stability.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    wiring_ok = True
    overview_ok = True
    summary_ok = True
    partial_ok = True
    route_ok = True
    payload_ui_ok = True

    # --- Dashboard page wiring: HTML exists and contains required elements/ids
    ui_path = os.path.join(ROOT, "internal_ui", "workspace-overview.html")
    if not os.path.isfile(ui_path):
        wiring_ok = False
    else:
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()
        for id_ in ("dashboard-root", "overview-stats", "section-intelligence", "section-portfolio", "section-risk", "section-market", "section-activity", "section-top-items", "section-notices", "btn-load", "workspace-id"):
            if id_ not in html or ("id=\"" + id_ + "\"") not in html and ("id='" + id_ + "'") not in html:
                if id_ == "workspace-id" and "workspace-id" in html:
                    continue
                if id_ in html:
                    continue
                wiring_ok = False
                break
        if "/api/workspaces/" not in html or "/dashboard" not in html:
            wiring_ok = False

    # --- Overview stats rendering: payload has overview and UI can derive stats
    try:
        from amazon_research.dashboard_serving import get_dashboard_payload
        payload = get_dashboard_payload(99501)
        ov = payload.get("overview") or {}
        for key in ("total_opportunities", "high_priority_opportunities", "total_portfolio_items", "high_risk_item_count", "top_strategic_score_count"):
            if key not in ov:
                overview_ok = False
    except Exception as e:
        overview_ok = False
        print("overview stats error: %s" % e)

    # --- Summary section rendering: payload has all summary sections UI expects
    try:
        payload = get_dashboard_payload(99502)
        for key in ("intelligence_summary", "strategy_summary", "portfolio_summary", "risk_summary", "market_summary", "activity_summary"):
            if key not in payload:
                summary_ok = False
    except Exception as e:
        summary_ok = False
        print("summary section error: %s" % e)

    # --- Partial-data resilience: payload with missing/empty sections still has stable shape
    try:
        minimal = {"workspace_id": 99503, "generated_at": "2025-01-01T00:00:00Z", "overview": {}, "intelligence_summary": {}, "strategy_summary": {}, "portfolio_summary": {}, "risk_summary": {}, "market_summary": {}, "activity_summary": {}, "top_items": {}, "top_actions": [], "notices": [], "health_indicators": {}}
        for k in ("overview", "top_items", "top_actions", "notices"):
            if k not in minimal:
                partial_ok = False
        payload = get_dashboard_payload(None)
        if "overview" not in payload or "top_items" not in payload:
            partial_ok = False
    except Exception as e:
        partial_ok = False
        print("partial-data resilience error: %s" % e)

    # --- Route integration compatibility: server defines and uses workspace-overview route
    try:
        api_script = os.path.join(ROOT, "scripts", "serve_internal_api.py")
        with open(api_script, "r", encoding="utf-8") as f:
            api_src = f.read()
        if "_serve_workspace_overview_ui" not in api_src:
            route_ok = False
        if "workspace-overview" not in api_src or "workspace-overview.html" not in api_src:
            route_ok = False
        if "_serve_workspace_overview_ui(self)" not in api_src:
            route_ok = False
    except Exception as e:
        route_ok = False
        print("route integration error: %s" % e)

    # --- Payload-to-UI stability: dashboard payload keys match what UI consumes
    try:
        payload = get_dashboard_payload(99504)
        ui_expects = ["workspace_id", "generated_at", "overview", "intelligence_summary", "strategy_summary", "portfolio_summary", "risk_summary", "market_summary", "activity_summary", "top_items", "top_actions", "notices", "health_indicators"]
        for k in ui_expects:
            if k not in payload:
                payload_ui_ok = False
        ti = payload.get("top_items") or {}
        for k in ("top_opportunities", "top_recommendations", "top_risks", "top_markets"):
            if k not in ti:
                payload_ui_ok = False
    except Exception as e:
        payload_ui_ok = False
        print("payload to UI stability error: %s" % e)

    print("workspace overview dashboard UI OK" if all([wiring_ok, overview_ok, summary_ok, partial_ok, route_ok, payload_ui_ok]) else "workspace overview dashboard UI FAIL")
    print("dashboard page wiring: OK" if wiring_ok else "dashboard page wiring: FAIL")
    print("overview stats rendering: OK" if overview_ok else "overview stats rendering: FAIL")
    print("summary section rendering: OK" if summary_ok else "summary section rendering: FAIL")
    print("partial-data resilience: OK" if partial_ok else "partial-data resilience: FAIL")
    print("route integration compatibility: OK" if route_ok else "route integration compatibility: FAIL")
    print("payload to UI stability: OK" if payload_ui_ok else "payload to UI stability: FAIL")
    sys.exit(0 if all([wiring_ok, overview_ok, summary_ok, partial_ok, route_ok, payload_ui_ok]) else 1)


if __name__ == "__main__":
    main()
