#!/usr/bin/env python3
"""
Step 211 smoke test: Dashboard data serving layer.
Validates dashboard payload generation, overview rollup, top item aggregation,
partial upstream fallback, workspace isolation compatibility, payload stability.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    from amazon_research.dashboard_serving import get_dashboard_payload
    from amazon_research.api import get_workspace_dashboard_response
    from amazon_research.workspace_isolation import require_workspace_context

    payload_ok = True
    overview_ok = True
    top_items_ok = True
    fallback_ok = True
    isolation_ok = True
    stability_ok = True

    # --- Dashboard payload generation: get_dashboard_payload returns full structure
    try:
        payload = get_dashboard_payload(99601)
        if not isinstance(payload, dict):
            payload_ok = False
        if payload.get("workspace_id") != 99601 or "generated_at" not in payload:
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"dashboard payload generation error: {e}")

    # --- Overview rollup generation: overview has expected keys
    try:
        payload = get_dashboard_payload(99602)
        ov = payload.get("overview") or {}
        for key in ("total_opportunities", "high_priority_opportunities", "total_portfolio_items", "high_risk_item_count", "top_strategic_score_count", "last_updated"):
            if key not in ov:
                overview_ok = False
    except Exception as e:
        overview_ok = False
        print(f"overview rollup generation error: {e}")

    # --- Top item aggregation: top_items has top_opportunities, top_recommendations, top_risks, top_markets
    try:
        payload = get_dashboard_payload(99603)
        ti = payload.get("top_items") or {}
        if not isinstance(ti.get("top_opportunities"), list):
            top_items_ok = False
        if not isinstance(ti.get("top_recommendations"), list):
            top_items_ok = False
        if not isinstance(ti.get("top_risks"), list):
            top_items_ok = False
        if not isinstance(ti.get("top_markets"), list):
            top_items_ok = False
    except Exception as e:
        top_items_ok = False
        print(f"top item aggregation error: {e}")

    # --- Partial upstream fallback: payload still stable when some upstream fails (e.g. workspace with no data)
    try:
        payload = get_dashboard_payload(99604)
        if "overview" not in payload or "top_items" not in payload:
            fallback_ok = False
        if "health_indicators" not in payload:
            fallback_ok = False
        payload_none = get_dashboard_payload(None)
        if not isinstance(payload_none, dict) or "overview" not in payload_none:
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"partial upstream fallback error: {e}")

    # --- Workspace isolation compatibility: payload is workspace-scoped; isolation guard exists
    try:
        if not require_workspace_context(99605, "dashboard_smoke"):
            isolation_ok = False
        payload_a = get_dashboard_payload(99605)
        payload_b = get_dashboard_payload(99606)
        if payload_a.get("workspace_id") != 99605 or payload_b.get("workspace_id") != 99606:
            isolation_ok = False
    except Exception as e:
        isolation_ok = False
        print(f"workspace isolation compatibility error: {e}")

    # --- Payload stability: required top-level keys present
    try:
        payload = get_dashboard_payload(99607)
        required = ("workspace_id", "generated_at", "overview", "intelligence_summary", "strategy_summary", "portfolio_summary", "risk_summary", "market_summary", "activity_summary", "top_items", "top_actions", "notices", "health_indicators")
        for key in required:
            if key not in payload:
                stability_ok = False
        body = get_workspace_dashboard_response(99607)
        if body.get("data") and "overview" not in body["data"]:
            stability_ok = False
    except Exception as e:
        stability_ok = False
        print(f"payload stability error: {e}")

    print("dashboard data serving OK" if all([payload_ok, overview_ok, top_items_ok, fallback_ok, isolation_ok, stability_ok]) else "dashboard data serving FAIL")
    print("dashboard payload generation: OK" if payload_ok else "dashboard payload generation: FAIL")
    print("overview rollup generation: OK" if overview_ok else "overview rollup generation: FAIL")
    print("top item aggregation: OK" if top_items_ok else "top item aggregation: FAIL")
    print("partial upstream fallback: OK" if fallback_ok else "partial upstream fallback: FAIL")
    print("workspace isolation compatibility: OK" if isolation_ok else "workspace isolation compatibility: FAIL")
    print("payload stability: OK" if stability_ok else "payload stability: FAIL")
    sys.exit(0 if all([payload_ok, overview_ok, top_items_ok, fallback_ok, isolation_ok, stability_ok]) else 1)


if __name__ == "__main__":
    main()
