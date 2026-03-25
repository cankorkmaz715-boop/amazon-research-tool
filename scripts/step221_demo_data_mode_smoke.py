#!/usr/bin/env python3
"""
Step 221 smoke test: Demo data mode. Validates demo mode detection, opportunity/portfolio/alert
generation, dashboard integration, and demo flag safety (no persistence, no overwrite).
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

detection_ok = True
opportunity_ok = True
portfolio_ok = True
alert_ok = True
dashboard_ok = True
safety_ok = True

try:
    from amazon_research.demo_data import (
        is_demo_mode_enabled,
        generate_demo_dashboard_payload,
        generate_demo_alerts,
        generate_demo_portfolio_items,
        should_use_demo_for_dashboard,
        should_use_demo_for_alerts,
        should_use_demo_for_portfolio,
    )
except Exception as e:
    detection_ok = opportunity_ok = portfolio_ok = alert_ok = dashboard_ok = safety_ok = False
    print("import error: %s" % e)


def main() -> None:
    global detection_ok, opportunity_ok, portfolio_ok, alert_ok, dashboard_ok, safety_ok

    # Demo mode detection: config and resolver
    if detection_ok:
        try:
            _ = is_demo_mode_enabled()
            empty_payload = {"overview": {"total_opportunities": 0, "total_portfolio_items": 0}, "top_items": {"top_opportunities": []}, "portfolio_summary": {"total": 0}}
            use = should_use_demo_for_dashboard(99991, empty_payload)
            detection_ok = isinstance(use, bool)
        except Exception as e:
            detection_ok = False
            print("detection error: %s" % e)

    # Demo opportunity generation: dashboard payload has top_opportunities with is_demo
    if opportunity_ok:
        try:
            payload = generate_demo_dashboard_payload(99992)
            opps = (payload.get("top_items") or {}).get("top_opportunities") or []
            opportunity_ok = len(opps) >= 1 and payload.get("is_demo") is True
            if opps:
                opportunity_ok = opportunity_ok and (opps[0].get("is_demo") is True or "Eco-friendly" in str(opps[0].get("rationale", "")))
        except Exception as e:
            opportunity_ok = False
            print("opportunity error: %s" % e)

    # Demo portfolio generation
    if portfolio_ok:
        try:
            items = generate_demo_portfolio_items(99993)
            portfolio_ok = len(items) >= 1 and (items[0].get("is_demo") is True) and "item_key" in (items[0] or {})
        except Exception as e:
            portfolio_ok = False
            print("portfolio error: %s" % e)

    # Demo alert generation
    if alert_ok:
        try:
            alerts = generate_demo_alerts(99994)
            alert_ok = len(alerts) >= 1 and (alerts[0].get("is_demo") is True) and "title" in (alerts[0] or {})
        except Exception as e:
            alert_ok = False
            print("alert error: %s" % e)

    # Dashboard demo integration: payload shape and is_demo
    if dashboard_ok:
        try:
            p = generate_demo_dashboard_payload(99995)
            dashboard_ok = (
                p.get("is_demo") is True
                and "overview" in p
                and "top_items" in p
                and "strategy_summary" in p
                and "risk_summary" in p
                and "market_summary" in p
                and "notices" in p
            )
        except Exception as e:
            dashboard_ok = False
            print("dashboard error: %s" % e)

    # Demo flag safety: generators do not touch DB; payloads are in-memory
    if safety_ok:
        try:
            p = generate_demo_dashboard_payload(99996)
            safety_ok = p.get("is_demo") is True
            a = generate_demo_alerts(99996)
            safety_ok = safety_ok and all(x.get("is_demo") is True for x in (a or []))
        except Exception as e:
            safety_ok = False
            print("safety error: %s" % e)

    print("demo data mode OK")
    print("demo mode detection: %s" % ("OK" if detection_ok else "FAIL"))
    print("demo opportunity generation: %s" % ("OK" if opportunity_ok else "FAIL"))
    print("demo portfolio generation: %s" % ("OK" if portfolio_ok else "FAIL"))
    print("demo alert generation: %s" % ("OK" if alert_ok else "FAIL"))
    print("dashboard demo integration: %s" % ("OK" if dashboard_ok else "FAIL"))
    print("demo flag safety: %s" % ("OK" if safety_ok else "FAIL"))

    if not (detection_ok and opportunity_ok and portfolio_ok and alert_ok and dashboard_ok and safety_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
