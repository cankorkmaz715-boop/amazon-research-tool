#!/usr/bin/env python3
"""Step 171: Signal drift detector – drift, spike, collapse, trend monitoring."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.monitoring.signal_drift_detector import (
        detect_drift,
        detect_collapse,
        detect_spike,
        detect_sudden_shift,
        detect_gradual_drift,
        run_drift_checks,
        DRIFT_GRADUAL,
        DRIFT_SPIKE,
        DRIFT_COLLAPSE,
        DRIFT_SUDDEN_SHIFT,
        SIGNAL_TREND,
    )

    def valid_report(r):
        return (
            isinstance(r, dict)
            and r.get("signal_type")
            and r.get("target_id") is not None
            and r.get("drift_type") in (DRIFT_GRADUAL, DRIFT_SPIKE, DRIFT_COLLAPSE, DRIFT_SUDDEN_SHIFT)
            and r.get("severity") in ("low", "medium", "high")
            and "timestamp" in r
        )

    # 1) Drift detection (general): detect_drift returns list of reports
    history = [10.0, 12.0, 11.0, 10.5, 10.0]
    reports = detect_drift(SIGNAL_TREND, current_value=25.0, history=history, target_id="T1")
    drift_ok = isinstance(reports, list)
    if reports:
        drift_ok = drift_ok and valid_report(reports[0])

    # 2) Spike detection: current >> recent avg
    spike_report = detect_spike(SIGNAL_TREND, 100.0, [5.0, 6.0, 5.5, 6.0, 5.0], target_id="T2")
    spike_ok = spike_report is not None and valid_report(spike_report) and spike_report.get("drift_type") == DRIFT_SPIKE

    # 3) Collapse detection: current near zero vs recent max
    collapse_report = detect_collapse(SIGNAL_TREND, 0.5, [50.0, 48.0, 52.0, 51.0], target_id="T3")
    collapse_ok = collapse_report is not None and valid_report(collapse_report) and collapse_report.get("drift_type") == DRIFT_COLLAPSE

    # 4) Trend monitoring: gradual drift and run_drift_checks
    gradual_report = detect_gradual_drift(SIGNAL_TREND, history=[20.0, 18.0, 15.0, 12.0, 8.0], target_id="T4")
    trend_ok = gradual_report is not None and valid_report(gradual_report) and gradual_report.get("drift_type") == DRIFT_GRADUAL
    out = run_drift_checks(
        current_context={"trend_score": 8.0, "demand_score": 70},
        history_contexts=[
            {"trend_score": 20.0, "demand_score": 72},
            {"trend_score": 18.0, "demand_score": 71},
            {"trend_score": 15.0, "demand_score": 70},
            {"trend_score": 12.0, "demand_score": 69},
            {"trend_score": 10.0, "demand_score": 70},
        ],
        target_id="T5",
    )
    trend_ok = trend_ok and isinstance(out.get("drifts"), list) and "timestamp" in out and "target_id" in out

    print("signal drift detector OK")
    print("drift detection: OK" if drift_ok else "drift detection: FAIL")
    print("spike detection: OK" if spike_ok else "spike detection: FAIL")
    print("collapse detection: OK" if collapse_ok else "collapse detection: FAIL")
    print("trend monitoring: OK" if trend_ok else "trend monitoring: FAIL")

    if not (drift_ok and spike_ok and collapse_ok and trend_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
