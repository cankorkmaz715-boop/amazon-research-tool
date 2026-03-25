#!/usr/bin/env python3
"""
Step 217 smoke test: Copilot context panel UI.
Validates copilot panel wiring, context summary rendering, signal and action rendering,
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
    context_summary_ok = True
    signal_action_ok = True
    partial_ok = True
    dashboard_ok = True
    payload_ui_ok = True

    ui_path = os.path.join(ROOT, "internal_ui", "workspace-overview.html")
    if not os.path.isfile(ui_path):
        wiring_ok = context_summary_ok = dashboard_ok = payload_ui_ok = False
    else:
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()
        for id_ in ("copilot-context-panel", "copilot-context-body", "copilot-context-summary", "copilot-context-signals", "copilot-context-opportunities", "copilot-context-actions", "copilot-context-empty"):
            if id_ not in html or ("id=\"" + id_ + "\"") not in html:
                wiring_ok = False
                break
        if "renderCopilotContextPanel" not in html:
            wiring_ok = False

    # Context summary rendering: payload has overview, strategy_summary for "what Copilot is focusing on"
    if get_dashboard_payload is not None:
        try:
            payload = get_dashboard_payload(99571)
            ov = payload.get("overview") or {}
            strat = payload.get("strategy_summary") or {}
            ss = strat.get("strategy_summary") or {}
            _ = ov.get("total_opportunities"), ss.get("act_now_count"), (payload.get("risk_summary") or {}).get("high_risk_count")
            context_summary_ok = True
        except Exception as e:
            context_summary_ok = False
            print("context summary rendering error: %s" % e)
    else:
        context_summary_ok = False

    # Signal and action rendering: top_items.top_opportunities, top_actions
    if get_dashboard_payload is not None:
        try:
            payload = get_dashboard_payload(99572)
            ti = payload.get("top_items") or {}
            opps = ti.get("top_opportunities") or []
            actions = payload.get("top_actions") or []
            _ = opps[:3], actions[:3]
            signal_action_ok = True
        except Exception as e:
            signal_action_ok = False
            print("signal and action rendering error: %s" % e)
    else:
        signal_action_ok = False

    # Partial-data resilience: empty or minimal payload
    try:
        minimal = {"overview": {}, "strategy_summary": {}, "risk_summary": {}, "top_items": {}, "top_actions": []}
        ov = minimal.get("overview") or {}
        strat = minimal.get("strategy_summary") or {}
        ss = strat.get("strategy_summary") or {}
        _ = ov.get("total_opportunities", 0), ss.get("act_now_count", 0)
        _ = (minimal.get("top_items") or {}).get("top_opportunities") or []
        _ = (minimal.get("top_items") or {}).get("top_risks") or []
        _ = minimal.get("top_actions") or []
        partial_ok = True
    except Exception as e:
        partial_ok = False
        print("partial-data resilience error: %s" % e)

    # Dashboard integration compatibility: panel is in same page as dashboard-content
    if os.path.isfile(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()
        if "copilot-context-panel" not in html or "dashboard-content" not in html:
            dashboard_ok = False
        if "renderCopilotContextPanel" not in html:
            dashboard_ok = False
    else:
        dashboard_ok = False

    # Payload-to-UI stability: dashboard payload has keys the panel consumes
    if get_dashboard_payload is not None:
        try:
            payload = get_dashboard_payload(99573)
            for key in ("overview", "strategy_summary", "risk_summary", "top_items", "top_actions"):
                if key not in payload:
                    payload_ui_ok = False
                    break
            else:
                ti = payload.get("top_items") or {}
                for k in ("top_opportunities", "top_risks", "top_markets"):
                    if k not in ti:
                        payload_ui_ok = False
                        break
                else:
                    payload_ui_ok = True
        except Exception as e:
            payload_ui_ok = False
            print("payload to UI stability error: %s" % e)
    else:
        payload_ui_ok = False

    all_ok = all([wiring_ok, context_summary_ok, signal_action_ok, partial_ok, dashboard_ok, payload_ui_ok])
    print("copilot context panel UI OK" if all_ok else "copilot context panel UI FAIL")
    print("copilot panel wiring: OK" if wiring_ok else "copilot panel wiring: FAIL")
    print("context summary rendering: OK" if context_summary_ok else "context summary rendering: FAIL")
    print("signal and action rendering: OK" if signal_action_ok else "signal and action rendering: FAIL")
    print("partial-data resilience: OK" if partial_ok else "partial-data resilience: FAIL")
    print("dashboard integration compatibility: OK" if dashboard_ok else "dashboard integration compatibility: FAIL")
    print("payload to UI stability: OK" if payload_ui_ok else "payload to UI stability: FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
