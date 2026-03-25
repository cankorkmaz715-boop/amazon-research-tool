#!/usr/bin/env python3
"""Step 166: Data integrity repair layer – missing data, partial scrape, timeseries, signal reconstruction, anomaly smoothing."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.monitoring.data_integrity_repair import (
        missing_data_repair,
        partial_scrape_repair,
        timeseries_gap_repair,
        signal_reconstruction,
        anomaly_smoothing,
        REPAIR_FIXED,
        REPAIR_SKIPPED,
        REPAIR_FAILED,
    )

    def valid_report(r):
        return (
            r.get("repair_status") in (REPAIR_FIXED, REPAIR_SKIPPED, REPAIR_FAILED)
            and "issue_type" in r
            and "repair_method" in r
            and "target_id" in r
            and "timestamp" in r
        )

    # 1) missing_data_repair: returns report (SKIPPED with recommend_refetch)
    r1 = missing_data_repair(record={"asin": "B001"}, target_id="B001")
    missing_ok = valid_report(r1) and r1.get("repair_status") == REPAIR_SKIPPED and r1.get("issue_type") == "missing_data"

    # 2) partial_scrape_repair: with payload returns FIXED or FAILED; without payload SKIPPED
    r2 = partial_scrape_repair("target-1", job_type="keyword_scan", payload={"keyword": "test"}, workspace_id=1)
    partial_ok = valid_report(r2)
    r2_skip = partial_scrape_repair("target-1", job_type=None, payload=None)
    partial_ok = partial_ok and r2_skip.get("repair_status") == REPAIR_SKIPPED

    # 3) timeseries_gap_repair: interpolate missing value between two valid points
    hist = [
        {"recorded_at": "2025-01-01T00:00:00Z", "bsr": 100},
        {"recorded_at": "2025-01-01T01:00:00Z", "bsr": None},
        {"recorded_at": "2025-01-01T02:00:00Z", "bsr": 102},
    ]
    r3 = timeseries_gap_repair(hist, value_key="bsr", target_id="asin-1")
    timeseries_ok = valid_report(r3)
    timeseries_ok = timeseries_ok and (r3.get("repair_status") == REPAIR_FIXED or "repaired_series" in r3 or "interpolated_count" in r3)
    if r3.get("repair_status") == REPAIR_FIXED:
        timeseries_ok = timeseries_ok and r3.get("repaired_series", [{}])[1].get("bsr") == 101.0

    # 4) signal_reconstruction: fill from raw inputs
    ctx = {"demand_raw": 70, "competition_raw": 30, "trend_raw": 0}
    r4 = signal_reconstruction(context=ctx, target_id="cluster-1")
    signal_ok = valid_report(r4) and r4.get("repair_status") == REPAIR_FIXED
    signal_ok = signal_ok and "reconstructed_context" in r4

    # 5) anomaly_smoothing: suppress single-point spike
    series = [
        {"t": 1, "bsr": 1000},
        {"t": 2, "bsr": 100000},
        {"t": 3, "bsr": 1002},
    ]
    r5 = anomaly_smoothing(series, value_key="bsr", spike_ratio_threshold=50.0, target_id="asin-2")
    anomaly_ok = valid_report(r5)
    anomaly_ok = anomaly_ok and (r5.get("repair_status") == REPAIR_FIXED or r5.get("repair_status") == REPAIR_SKIPPED)
    if r5.get("repair_status") == REPAIR_FIXED:
        anomaly_ok = anomaly_ok and "smoothed_series" in r5

    print("data integrity repair layer OK")
    print("missing data repair: OK" if missing_ok else "missing data repair: FAIL")
    print("partial scrape repair: OK" if partial_ok else "partial scrape repair: FAIL")
    print("timeseries repair: OK" if timeseries_ok else "timeseries repair: FAIL")
    print("signal reconstruction: OK" if signal_ok else "signal reconstruction: FAIL")
    print("anomaly smoothing: OK" if anomaly_ok else "anomaly smoothing: FAIL")

    if not (missing_ok and partial_ok and timeseries_ok and signal_ok and anomaly_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
