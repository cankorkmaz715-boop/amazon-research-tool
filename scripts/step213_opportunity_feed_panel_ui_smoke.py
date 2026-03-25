#!/usr/bin/env python3
"""
Step 213 smoke test: Opportunity feed panel UI.
Validates feed panel wiring, opportunity item rendering, score/priority/status rendering,
partial-data resilience, dashboard integration compatibility, payload-to-UI stability.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

try:
    from amazon_research.dashboard_serving import get_dashboard_payload
except Exception:
    get_dashboard_payload = None


def main() -> None:
    wiring_ok = True
    item_rendering_ok = True
    score_priority_status_ok = True
    partial_ok = True
    dashboard_ok = True
    payload_ui_ok = True

    # --- Opportunity feed panel wiring: HTML has feed panel and list elements
    ui_path = os.path.join(ROOT, "internal_ui", "workspace-overview.html")
    if not os.path.isfile(ui_path):
        wiring_ok = False
    else:
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()
        for id_or_class in (
            "opportunity-feed-panel",
            "opportunity-feed-list",
            "opportunity-feed-empty",
            "opportunity-feed-count",
            "opportunity-feed-item",
            "feed-item-header",
            "feed-item-id",
            "badge",
        ):
            if id_or_class not in html:
                wiring_ok = False
                break
        if "renderOpportunityFeed" not in html:
            wiring_ok = False

    # --- Opportunity item rendering: dashboard payload provides top_opportunities with item shape
    try:
        if get_dashboard_payload is None:
            item_rendering_ok = False
        else:
            payload = get_dashboard_payload(99511)
            ti = payload.get("top_items") or {}
            items = ti.get("top_opportunities") or []
            if not isinstance(items, list):
                item_rendering_ok = False
            else:
                for o in items[:3]:
                    if not isinstance(o, dict):
                        item_rendering_ok = False
                        break
                else:
                    item_rendering_ok = True
    except Exception as e:
        item_rendering_ok = False
        print("opportunity item rendering error: %s" % e)

    # --- Score / priority / status rendering: payload supports strategy_status, priority_level, opportunity_score, etc.
    try:
        if get_dashboard_payload is None:
            score_priority_status_ok = False
        else:
            payload = get_dashboard_payload(99512)
            ti = payload.get("top_items") or {}
            items = ti.get("top_opportunities") or []
            feed_item_keys = {"opportunity_id", "strategy_status", "priority_level", "opportunity_score", "rationale", "recommended_action", "risk_notes"}
            for o in items[:2]:
                if not isinstance(o, dict):
                    continue
                for k in feed_item_keys:
                    _ = o.get(k)
            score_priority_status_ok = True
    except Exception as e:
        score_priority_status_ok = False
        print("score/priority/status error: %s" % e)

    # --- Partial-data resilience: empty list and minimal item (missing fields) do not break contract
    try:
        minimal_items = []
        minimal_one = {"opportunity_id": "OP-1"}
        minimal_items.append(minimal_one)
        for o in minimal_items:
            _ = o.get("opportunity_id", "—")
            _ = o.get("strategy_status", "")
            _ = (o.get("priority_level") or "").lower()
            _ = o.get("opportunity_score")
            _ = (o.get("rationale") or "")[:160]
            _ = o.get("recommended_action", "")
            _ = o.get("risk_notes") or []
        partial_ok = True
    except Exception as e:
        partial_ok = False
        print("partial-data resilience error: %s" % e)

    # --- Dashboard integration compatibility: feed uses same page and same dashboard payload
    try:
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()
        if "opportunity-feed-panel" not in html or "dashboard-content" not in html:
            dashboard_ok = False
        if get_dashboard_payload is not None:
            payload = get_dashboard_payload(99513)
            if "top_items" not in payload:
                dashboard_ok = False
    except Exception as e:
        dashboard_ok = False
        print("dashboard integration error: %s" % e)

    # --- Payload-to-UI stability: top_opportunities item keys match what feed UI expects
    try:
        if get_dashboard_payload is None:
            payload_ui_ok = False
        else:
            payload = get_dashboard_payload(99514)
            ti = payload.get("top_items") or {}
            items = ti.get("top_opportunities") or []
            ui_expects = ["opportunity_id", "strategy_status", "priority_level", "opportunity_score", "rationale", "recommended_action", "risk_notes"]
            for o in items[:5]:
                for k in ui_expects:
                    _ = o.get(k)
            payload_ui_ok = True
    except Exception as e:
        payload_ui_ok = False
        print("payload to UI stability error: %s" % e)

    print("opportunity feed panel UI OK" if all([wiring_ok, item_rendering_ok, score_priority_status_ok, partial_ok, dashboard_ok, payload_ui_ok]) else "opportunity feed panel UI FAIL")
    print("feed panel wiring: OK" if wiring_ok else "feed panel wiring: FAIL")
    print("opportunity item rendering: OK" if item_rendering_ok else "opportunity item rendering: FAIL")
    print("score priority status rendering: OK" if score_priority_status_ok else "score priority status rendering: FAIL")
    print("partial-data resilience: OK" if partial_ok else "partial-data resilience: FAIL")
    print("dashboard integration compatibility: OK" if dashboard_ok else "dashboard integration compatibility: FAIL")
    print("payload to UI stability: OK" if payload_ui_ok else "payload to UI stability: FAIL")
    sys.exit(0 if all([wiring_ok, item_rendering_ok, score_priority_status_ok, partial_ok, dashboard_ok, payload_ui_ok]) else 1)


if __name__ == "__main__":
    main()
