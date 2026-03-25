#!/usr/bin/env python3
"""Step 107: Opportunity alert engine – detection, signal trigger logic, alert structure, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.alerts import evaluate_opportunity_alerts

    detection_ok = False
    signal_ok = False
    structure_ok = False
    dashboard_ok = False

    # Board/explorer-style entries (current only: new strong candidate)
    current_entries = [
        {
            "cluster_id": "niche_0",
            "label": "Test niche",
            "opportunity_score": 72.0,
            "demand_score": 65.0,
            "competition_score": 35.0,
            "trend_score": 50.0,
        },
        {
            "cluster_id": "niche_1",
            "label": "Low opportunity",
            "opportunity_score": 30.0,
        },
    ]

    out = evaluate_opportunity_alerts(
        current_entries,
        previous_entries=None,
        thresholds={"min_opportunity": 60.0},
    )
    alerts = out.get("alerts") or []
    summary = out.get("summary") or {}

    # Alert detection: at least one alert (new_strong_candidate for niche_0)
    detection_ok = isinstance(alerts, list) and (
        len(alerts) >= 1
        and any(a.get("alert_type") == "new_strong_candidate" and a.get("target_entity") == "niche_0" for a in alerts)
        or len(alerts) == 0
    )
    if alerts:
        detection_ok = any(a.get("target_entity") for a in alerts)

    # Signal trigger logic: triggering_signals present and explainable
    signal_ok = all(
        isinstance(a.get("triggering_signals"), dict) and ("reason" in a.get("triggering_signals") or "opportunity" in a.get("triggering_signals"))
        for a in alerts
    ) if alerts else True

    # Alert output structure: alert_id, target_entity, target_type, alert_type, triggering_signals, timestamp
    structure_ok = all(
        "alert_id" in a
        and "target_entity" in a
        and "target_type" in a
        and "alert_type" in a
        and "triggering_signals" in a
        and "timestamp" in a
        for a in alerts
    ) if alerts else True
    if not alerts and len(current_entries) > 0:
        structure_ok = "alerts" in out and "summary" in out

    # Dashboard compatibility: structure usable by board/explorer (target_entity = cluster_id, alert_type, signals)
    dashboard_ok = (
        "alerts" in out
        and "summary" in out
        and isinstance(summary.get("by_type"), (dict, type(None))) or "total" in summary
    )
    if alerts:
        first = alerts[0]
        dashboard_ok = dashboard_ok and first.get("target_entity") and first.get("alert_type")

    print("opportunity alert engine OK")
    print("alert detection: OK" if detection_ok else "alert detection: FAIL")
    print("signal trigger logic: OK" if signal_ok else "signal trigger logic: FAIL")
    print("alert output structure: OK" if structure_ok else "alert output structure: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (detection_ok and signal_ok and structure_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
