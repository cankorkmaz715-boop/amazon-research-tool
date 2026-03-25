#!/usr/bin/env python3
"""Step 115: Workspace cost insight layer – cost aggregation, bandwidth attribution, job cost, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import get_workspace_cost_insight

    workspace_id = 1
    insight = get_workspace_cost_insight(workspace_id, since_days=30)

    drivers = insight.get("estimated_cost_drivers") or {}
    cost_agg_ok = (
        isinstance(drivers, dict)
        and "discovery" in drivers
        and "refresh" in drivers
        and "export" in drivers
        and "alerts" in drivers
    )

    bandwidth = insight.get("bandwidth_attribution") or {}
    bandwidth_ok = (
        isinstance(bandwidth, dict)
        and "estimated_pages" in bandwidth
        and "estimated_bytes" in bandwidth
        and "by_driver" in bandwidth
    )

    job_cost = insight.get("job_cost_visibility") or {}
    job_ok = (
        isinstance(job_cost, dict)
        and "completed" in job_cost
        and "failed" in job_cost
        and "total_processed" in job_cost
    )

    summary = insight.get("cost_summary") or {}
    dashboard_ok = (
        insight.get("workspace_id") == workspace_id
        and "since_days" in insight
        and "heavy_usage_areas" in insight
        and isinstance(insight["heavy_usage_areas"], list)
        and isinstance(summary, dict)
        and "total_estimated_units" in summary
        and summary.get("level") in ("low", "medium", "high")
    )

    print("workspace cost insight layer OK")
    print("cost aggregation: OK" if cost_agg_ok else "cost aggregation: FAIL")
    print("bandwidth attribution: OK" if bandwidth_ok else "bandwidth attribution: FAIL")
    print("job cost visibility: OK" if job_ok else "job cost visibility: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (cost_agg_ok and bandwidth_ok and job_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
