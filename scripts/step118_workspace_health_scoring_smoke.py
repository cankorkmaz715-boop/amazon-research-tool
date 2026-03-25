#!/usr/bin/env python3
"""Step 118: Workspace health scoring – health score, status label, signal explanation, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

VALID_STATUSES = ("healthy", "warning", "critical")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import get_workspace_health

    workspace_id = 1
    result = get_workspace_health(workspace_id, since_days=30)

    health_score_ok = (
        isinstance(result.get("health_score"), (int, float))
        and 0 <= result["health_score"] <= 100
    )

    status = result.get("health_status") or ""
    status_ok = status in VALID_STATUSES

    explanation = result.get("explanation")
    signal_ok = (
        "explanation" in result
        and isinstance(explanation, str)
        and "contributing_signals" in result
        and isinstance(result["contributing_signals"], dict)
    )
    signals = result.get("contributing_signals") or {}
    signal_ok = signal_ok and (
        "quota_pressure" in signals
        and "alert_intensity" in signals
        and "cost_pressure" in signals
        and "activity_balance" in signals
    )

    dashboard_ok = (
        result.get("workspace_id") == workspace_id
        and "health_score" in result
        and "health_status" in result
        and "explanation" in result
        and "contributing_signals" in result
    )

    print("workspace health scoring OK")
    print("health score: OK" if health_score_ok else "health score: FAIL")
    print("status label: OK" if status_ok else "status label: FAIL")
    print("signal explanation: OK" if signal_ok else "signal explanation: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (health_score_ok and status_ok and signal_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
