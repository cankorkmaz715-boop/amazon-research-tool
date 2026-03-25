#!/usr/bin/env python3
"""Step 117: Historical workspace analytics view – history read, trend aggregation, dashboard structure, snapshot compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import get_historical_workspace_analytics

    workspace_id = 1
    view = get_historical_workspace_analytics(workspace_id, limit=30)

    history_ok = (
        isinstance(view, dict)
        and view.get("workspace_id") == workspace_id
        and "snapshots_used" in view
        and isinstance(view.get("snapshots_used"), (int, float))
    )

    trends = view.get("trends") or {}
    trend_names = [
        "usage_trend",
        "quota_pressure_trend",
        "cost_trend",
        "alert_volume_trend",
        "discovery_activity_trend",
        "refresh_activity_trend",
        "opportunity_generation_trend",
    ]
    trend_agg_ok = all(
        name in trends and isinstance(trends[name], list) for name in trend_names
    )
    for name in trend_names:
        if trends.get(name):
            pt = trends[name][0]
            trend_agg_ok = trend_agg_ok and "snapshot_at" in pt and "value" in pt

    dashboard_ok = (
        "workspace_id" in view
        and "trends" in view
        and "snapshots_used" in view
        and len(trend_names) == len([k for k in trend_names if k in trends])
    )

    snapshot_compat_ok = True
    if view.get("snapshots_used", 0) > 0 and trends.get("cost_trend"):
        pt = trends["cost_trend"][0]
        snapshot_compat_ok = isinstance(pt.get("value"), (int, float)) and (
            isinstance(pt.get("snapshot_at"), str) or pt.get("snapshot_at") is not None
        )

    print("historical workspace analytics view OK")
    print("history read: OK" if history_ok else "history read: FAIL")
    print("trend aggregation: OK" if trend_agg_ok else "trend aggregation: FAIL")
    print("dashboard structure: OK" if dashboard_ok else "dashboard structure: FAIL")
    print("snapshot compatibility: OK" if snapshot_compat_ok else "snapshot compatibility: FAIL")

    if not (history_ok and trend_agg_ok and dashboard_ok and snapshot_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
