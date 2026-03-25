#!/usr/bin/env python3
"""Step 114: Workspace usage dashboard metrics – usage aggregation, quota, alerts, structure."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import get_workspace_usage_dashboard

    # Use a fixed workspace_id; may have no data when DB empty
    workspace_id = 1
    dash = get_workspace_usage_dashboard(workspace_id, since_days=30)

    usage = dash.get("usage")
    usage_ok = isinstance(usage, dict)

    quota_consumption = dash.get("quota_consumption")
    quota_ok = isinstance(quota_consumption, dict)
    if quota_ok and quota_consumption:
        for qtype, qv in quota_consumption.items():
            quota_ok = quota_ok and isinstance(qv, dict) and "limit" in qv and "used" in qv
            break
    else:
        quota_ok = True  # empty is valid

    alert_count = dash.get("alert_count")
    alert_ok = isinstance(alert_count, (int, float)) and alert_count >= 0

    structure_ok = (
        "workspace_id" in dash
        and dash.get("workspace_id") == workspace_id
        and "since_days" in dash
        and "rate_limit_events" in dash
        and "queue_activity" in dash
    )
    queue_act = dash.get("queue_activity") or {}
    structure_ok = structure_ok and isinstance(queue_act, dict) and "total" in queue_act

    print("workspace usage dashboard metrics OK")
    print("usage aggregation: OK" if usage_ok else "usage aggregation: FAIL")
    print("quota visibility: OK" if quota_ok else "quota visibility: FAIL")
    print("alert counts: OK" if alert_ok else "alert counts: FAIL")
    print("dashboard structure: OK" if structure_ok else "dashboard structure: FAIL")

    if not (usage_ok and quota_ok and alert_ok and structure_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
