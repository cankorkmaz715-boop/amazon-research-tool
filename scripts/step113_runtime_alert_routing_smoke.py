#!/usr/bin/env python3
"""Step 113: Runtime alert routing – severity, source, workspace, routing output structure."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_KEYS = ("alert_id", "route_target_type", "route_reason", "severity", "timestamp")


def _valid_record(r: dict) -> bool:
    return all(k in r and r[k] is not None for k in REQUIRED_KEYS)


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import (
        route_event,
        route_health_event,
        route_opportunity_alert,
        route_worker_event,
        route_quota_event,
        SOURCE_HEALTH_MONITOR,
        SOURCE_OPPORTUNITY_ALERT,
        SOURCE_WORKER_QUEUE,
        SOURCE_QUOTA,
        SEVERITY_WARNING,
        SEVERITY_CRITICAL,
    )

    # Severity routing: critical -> ops, warning -> dashboard
    health_critical = {
        "overall": "critical",
        "components": {"queue": {"status": "critical", "message": "queue backlog 600"}},
        "evaluated_at": "2025-01-01T12:00:00Z",
    }
    routes_health = route_health_event(health_critical)
    severity_ok = (
        len(routes_health) >= 1
        and routes_health[0].get("severity") == SEVERITY_CRITICAL
        and routes_health[0].get("route_target_type") == "ops"
    )

    # Source routing: each source produces expected structure
    opp_alert = {
        "alert_id": "test-uuid-1",
        "target_entity": "cluster-1",
        "alert_type": "opportunity_increase",
        "triggering_signals": {"reason": "opportunity +10"},
        "timestamp": "2025-01-01T12:00:00Z",
    }
    routes_opp = route_opportunity_alert(opp_alert)
    source_ok = (
        len(routes_opp) == 1
        and _valid_record(routes_opp[0])
        and routes_opp[0].get("source_type") == SOURCE_OPPORTUNITY_ALERT
    )

    # Workspace context
    routes_opp_ws = route_opportunity_alert(opp_alert, workspace_id=42)
    workspace_ok = (
        len(routes_opp_ws) == 1
        and routes_opp_ws[0].get("workspace_id") == 42
    )
    routes_health_ws = route_health_event(health_critical, workspace_id=99)
    workspace_ok = workspace_ok and (
        (len(routes_health_ws) >= 1 and routes_health_ws[0].get("workspace_id") == 99)
        or len(routes_health_ws) == 0
    )
    if routes_health_ws:
        workspace_ok = workspace_ok and routes_health_ws[0].get("workspace_id") == 99

    # Routing output structure: all required keys
    worker_ev = {"event_type": "job_failed", "message": "Job 1 failed", "timestamp": "2025-01-01T12:00:00Z"}
    quota_ev = {"message": "quota exceeded", "workspace_id": 1, "timestamp": "2025-01-01T12:00:00Z"}
    routes_worker = route_worker_event(worker_ev)
    routes_quota = route_quota_event(quota_ev)
    structure_ok = (
        all(_valid_record(r) for r in routes_health + routes_opp + routes_worker + routes_quota)
        and all(r.get("route_target_type") in ("dashboard", "ops") for r in routes_opp + routes_worker + routes_quota)
    )

    # route_event entry point
    via_entry = route_event(opp_alert, SOURCE_OPPORTUNITY_ALERT, workspace_id=7)
    structure_ok = structure_ok and len(via_entry) == 1 and _valid_record(via_entry[0]) and via_entry[0].get("workspace_id") == 7

    print("runtime alert routing OK")
    print("severity routing: OK" if severity_ok else "severity routing: FAIL")
    print("source routing: OK" if source_ok else "source routing: FAIL")
    print("workspace context: OK" if workspace_ok else "workspace context: FAIL")
    print("routing output structure: OK" if structure_ok else "routing output structure: FAIL")

    if not (severity_ok and source_ok and workspace_ok and structure_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
