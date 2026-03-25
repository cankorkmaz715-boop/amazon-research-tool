#!/usr/bin/env python3
"""Step 173: Anomaly alert engine – anomaly detection, severity, signal integration, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.discovery.anomaly_alert_engine import (
        detect_anomalies_from_drift,
        detect_anomalies_from_lifecycle,
        detect_demand_breakdown,
        detect_competition_surge,
        get_anomaly_alerts,
        get_anomaly_alerts_for_opportunity,
        to_prioritized_alert,
        ANOMALY_TREND_SPIKE,
        ANOMALY_SCORE_COLLAPSE,
        ANOMALY_DEMAND_BREAKDOWN,
        ANOMALY_LIFECYCLE_TRANSITION,
    )

    def valid_alert(a):
        return (
            isinstance(a, dict)
            and a.get("alert_id")
            and a.get("target_entity") is not None
            and a.get("anomaly_type")
            and a.get("severity") in ("low", "medium", "high", "critical")
            and "supporting_signal_summary" in a
            and "timestamp" in a
        )

    # 1) Anomaly detection from drift (collapse -> score_collapse, spike -> trend_spike)
    drift_collapse = [{"drift_type": "collapse", "signal_type": "trend_score", "severity": "high", "target_id": "E1"}]
    alerts = detect_anomalies_from_drift(drift_collapse, target_entity="E1")
    detection_ok = len(alerts) >= 1 and valid_alert(alerts[0])
    drift_spike = [{"drift_type": "spike", "signal_type": "trend_score", "severity": "medium"}]
    alerts2 = detect_anomalies_from_drift(drift_spike, target_entity="E2")
    detection_ok = detection_ok and len(alerts2) >= 1 and alerts2[0].get("anomaly_type") == ANOMALY_TREND_SPIKE

    # 2) Severity classification (high/critical for collapse, medium for spike)
    severity_ok = alerts[0].get("severity") in ("low", "medium", "high", "critical")
    demand_alert = detect_demand_breakdown(5.0, [80.0, 75.0, 70.0], target_entity="E3")
    severity_ok = severity_ok and demand_alert is not None and demand_alert.get("severity") in ("medium", "high", "critical")

    # 3) Signal integration (lifecycle transition + drift)
    life = {"opportunity_id": "E4", "lifecycle_state": "fading", "lifecycle_score": 25}
    trans = detect_anomalies_from_lifecycle(life, previous_state="rising")
    signal_ok = isinstance(trans, list)
    if trans:
        signal_ok = signal_ok and valid_alert(trans[0]) and trans[0].get("anomaly_type") == ANOMALY_LIFECYCLE_TRANSITION
    agg = get_anomaly_alerts(target_entity="E5", drift_reports=drift_collapse, lifecycle_output=life)
    signal_ok = signal_ok and isinstance(agg, list)

    # 4) Dashboard compatibility (to_prioritized_alert)
    one = alerts[0]
    pri = to_prioritized_alert(one)
    dashboard_ok = isinstance(pri, dict) and ("priority_score" in pri or "priority_label" in pri) and "alert_id" in pri
    opp_alerts = get_anomaly_alerts_for_opportunity("test-ref", memory_record={"opportunity_ref": "test-ref", "score_history": [50, 48, 10]})
    dashboard_ok = dashboard_ok and isinstance(opp_alerts, list)

    print("anomaly alert engine OK")
    print("anomaly detection: OK" if detection_ok else "anomaly detection: FAIL")
    print("severity classification: OK" if severity_ok else "severity classification: FAIL")
    print("signal integration: OK" if signal_ok else "signal integration: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (detection_ok and severity_ok and signal_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
