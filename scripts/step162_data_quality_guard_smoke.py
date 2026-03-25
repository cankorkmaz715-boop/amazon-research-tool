#!/usr/bin/env python3
"""Step 162: Data quality guard – missing data, numeric range, history continuity, signal presence, anomaly detection."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.monitoring.data_quality_guard import (
        missing_data_check,
        numeric_range_check,
        history_continuity_check,
        signal_presence_check,
        anomaly_detection_check,
        run_all_checks,
        QUALITY_OK,
        QUALITY_WARNING,
        QUALITY_FAIL,
    )

    # 1) missing_data_check: returns list of issues; detects empty required fields
    issues_missing = missing_data_check(record={"asin": "B001"}, context=None)
    missing_ok = isinstance(issues_missing, list) and (len(issues_missing) >= 1 or "title" in str(issues_missing))
    issues_missing_full = missing_data_check(record={"asin": "B001", "title": "Product"}, context={})
    missing_ok = missing_ok and isinstance(issues_missing_full, list)

    # 2) numeric_range_check: returns list of issues; flags price <= 0, rating outside 0-5, review_count < 0
    issues_range = numeric_range_check(record={"price": -1, "rating": 6, "review_count": 0})
    range_ok = isinstance(issues_range, list) and len(issues_range) >= 1
    range_ok = range_ok and numeric_range_check(record={"price": 10, "rating": 4.5, "review_count": 100}) == []

    # 3) history_continuity_check: returns list of issues; detects large gaps
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    history_gap = [
        {"recorded_at": (now - timedelta(days=20)).isoformat(), "bsr": 1000},
        {"recorded_at": (now - timedelta(days=2)).isoformat(), "bsr": 900},
    ]
    issues_hist = history_continuity_check(history=history_gap, max_gap_days=7)
    history_ok = isinstance(issues_hist, list) and len(issues_hist) >= 1
    history_ok = history_ok and history_continuity_check(history=[]) == []

    # 4) signal_presence_check: returns list of issues; requires demand, competition, trend
    issues_sig = signal_presence_check(context={})
    signal_ok = isinstance(issues_sig, list) and len(issues_sig) >= 1
    signal_ok = signal_ok and signal_presence_check(context={"demand_score": 50, "competition_score": 30, "trend_score": 0}) == []

    # 5) anomaly_detection_check: returns list of issues; detects BSR spike (e.g. 500000 -> 50)
    history_spike = [{"recorded_at": now.isoformat(), "bsr": 500000}, {"recorded_at": (now).isoformat(), "bsr": 50}]
    issues_anom = anomaly_detection_check(history=history_spike, value_key="bsr", spike_ratio_threshold=100)
    anomaly_ok = isinstance(issues_anom, list) and len(issues_anom) >= 1
    anomaly_ok = anomaly_ok and anomaly_detection_check(history=[]) == []

    # run_all_checks returns data_quality and issues
    result = run_all_checks(record={"asin": "B002", "title": "X", "price": 9.99, "rating": 4.0, "review_count": 10})
    run_ok = "data_quality" in result and result["data_quality"] in (QUALITY_OK, QUALITY_WARNING, QUALITY_FAIL)
    run_ok = run_ok and "issues" in result and isinstance(result["issues"], list)

    print("data quality guard OK")
    print("missing data check: OK" if missing_ok else "missing data check: FAIL")
    print("numeric range check: OK" if range_ok else "numeric range check: FAIL")
    print("history continuity: OK" if history_ok else "history continuity: FAIL")
    print("signal presence: OK" if signal_ok else "signal presence: FAIL")
    print("anomaly detection: OK" if anomaly_ok else "anomaly detection: FAIL")

    if not (missing_ok and range_ok and history_ok and signal_ok and anomaly_ok and run_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
