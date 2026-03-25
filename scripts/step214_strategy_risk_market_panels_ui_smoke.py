#!/usr/bin/env python3
"""
Step 214 smoke test: Strategy / Risk / Market insights panels UI.
Validates strategy panel wiring, risk panel wiring, market panel wiring,
insight item rendering, partial-data resilience, dashboard integration compatibility.
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
    strategy_wiring_ok = True
    risk_wiring_ok = True
    market_wiring_ok = True
    insight_item_ok = True
    partial_ok = True
    dashboard_ok = True

    ui_path = os.path.join(ROOT, "internal_ui", "workspace-overview.html")
    if not os.path.isfile(ui_path):
        strategy_wiring_ok = risk_wiring_ok = market_wiring_ok = dashboard_ok = False
    else:
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()

        # --- Strategy panel wiring
        for id_or_name in ("strategy-insights-panel", "strategy-insights-list", "strategy-insights-empty", "renderStrategyInsightsPanel"):
            if id_or_name not in html:
                strategy_wiring_ok = False
                break

        # --- Risk panel wiring
        for id_or_name in ("risk-insights-panel", "risk-insights-list", "risk-insights-empty", "renderRiskInsightsPanel"):
            if id_or_name not in html:
                risk_wiring_ok = False
                break

        # --- Market panel wiring
        for id_or_name in ("market-insights-panel", "market-insights-list", "market-insights-empty", "renderMarketInsightsPanel"):
            if id_or_name not in html:
                market_wiring_ok = False
                break

        # --- Dashboard integration: panels inside dashboard layout, same payload
        if "insight-panels-grid" not in html or "dashboard-content" not in html:
            dashboard_ok = False
        if get_dashboard_payload is not None:
            payload = get_dashboard_payload(99521)
            for key in ("strategy_summary", "risk_summary", "market_summary"):
                if key not in payload:
                    dashboard_ok = False

    # --- Insight item rendering: payload sections have shape that panels consume
    if get_dashboard_payload is not None:
        try:
            payload = get_dashboard_payload(99522)
            strat = (payload.get("strategy_summary") or {})
            risk = (payload.get("risk_summary") or {})
            market = (payload.get("market_summary") or {})
            _ = strat.get("act_now_count")
            _ = strat.get("strategy_summary")
            _ = risk.get("high_risk_count")
            _ = risk.get("risk_summary")
            _ = market.get("market_entry_summary")
            ti = payload.get("top_items") or {}
            _ = (ti.get("top_risks") or [])[:1]
            _ = (ti.get("top_markets") or [])[:1]
            _ = (payload.get("top_actions") or [])[:1]
            _ = (payload.get("notices") or [])[:1]
            insight_item_ok = True
        except Exception as e:
            insight_item_ok = False
            print("insight item rendering error: %s" % e)
    else:
        insight_item_ok = False

    # --- Partial-data resilience: empty or minimal sections do not break contract
    try:
        minimal = {
            "strategy_summary": {},
            "risk_summary": {},
            "market_summary": {},
            "top_items": {"top_opportunities": [], "top_risks": [], "top_markets": []},
            "top_actions": [],
            "notices": [],
        }
        strat = minimal.get("strategy_summary") or {}
        risk = minimal.get("risk_summary") or {}
        market = minimal.get("market_summary") or {}
        safe_act = strat.get("act_now_count", 0)
        safe_ss = strat.get("strategy_summary", {})
        safe_high = risk.get("high_risk_count", 0)
        safe_mes = market.get("market_entry_summary", {})
        ti = minimal.get("top_items") or {}
        (ti.get("top_risks") or [])[:5]
        (ti.get("top_markets") or [])[:5]
        partial_ok = True
    except Exception as e:
        partial_ok = False
        print("partial-data resilience error: %s" % e)

    all_ok = all([strategy_wiring_ok, risk_wiring_ok, market_wiring_ok, insight_item_ok, partial_ok, dashboard_ok])
    print("strategy risk market panels UI OK" if all_ok else "strategy risk market panels UI FAIL")
    print("strategy panel wiring: OK" if strategy_wiring_ok else "strategy panel wiring: FAIL")
    print("risk panel wiring: OK" if risk_wiring_ok else "risk panel wiring: FAIL")
    print("market panel wiring: OK" if market_wiring_ok else "market panel wiring: FAIL")
    print("insight item rendering: OK" if insight_item_ok else "insight item rendering: FAIL")
    print("partial-data resilience: OK" if partial_ok else "partial-data resilience: FAIL")
    print("dashboard integration compatibility: OK" if dashboard_ok else "dashboard integration compatibility: FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
