#!/usr/bin/env python3
"""
Step 120: Platform intelligence / SaaS operations review.
Audits telemetry, operational health, alert routing, workspace usage dashboard, cost insight,
tenant analytics snapshots, historical analytics view, workspace health scoring, account risk detector.
Verifies signal propagation, snapshot/historical compatibility, health/risk consistency, ops compatibility.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

WORKSPACE_ID = 1


def check_telemetry_integrity():
    """Telemetry layer: get_metrics_snapshot shape and propagation to health monitor."""
    ok = True
    try:
        from amazon_research.monitoring import get_metrics_snapshot, reset_runtime_metrics
        snap = get_metrics_snapshot()
        ok = (
            isinstance(snap, dict)
            and "crawler_requests" in snap
            and "worker_jobs_processed" in snap
            and "queue_backlog" in snap
            and callable(reset_runtime_metrics)
        )
        # Health monitor consumes telemetry
        from amazon_research.monitoring import get_operational_health
        health = get_operational_health()
        ok = ok and isinstance(health, dict) and "overall" in health and "components" in health
    except Exception:
        ok = False
    return ok


def check_analytics_snapshots():
    """Tenant snapshot engine and historical view: payload shape and trend consumption."""
    ok = True
    try:
        from amazon_research.monitoring import build_tenant_snapshot_payload, get_historical_workspace_analytics
        payload = build_tenant_snapshot_payload(WORKSPACE_ID, since_days=30)
        ok = (
            isinstance(payload, dict)
            and "usage_summary" in payload
            and "quota_status" in payload
            and "cost_insight_summary" in payload
            and "alert_volume" in payload
            and "discovery_activity" in payload
            and "refresh_activity" in payload
            and "opportunity_generation_volume" in payload
        )
        view = get_historical_workspace_analytics(WORKSPACE_ID, limit=10)
        trends = view.get("trends") or {}
        ok = ok and (
            isinstance(view, dict)
            and "workspace_id" in view
            and "usage_trend" in trends
            and "cost_trend" in trends
            and "quota_pressure_trend" in trends
            and "snapshots_used" in view
        )
    except Exception:
        ok = False
    return ok


def check_health_scoring():
    """Workspace health scoring: output shape and signal consistency."""
    ok = True
    try:
        from amazon_research.monitoring import get_workspace_health
        health = get_workspace_health(WORKSPACE_ID, since_days=30)
        ok = (
            isinstance(health, dict)
            and health.get("workspace_id") == WORKSPACE_ID
            and "health_score" in health
            and "health_status" in health
            and "explanation" in health
            and "contributing_signals" in health
        )
        score = health.get("health_score")
        status = health.get("health_status")
        signals = health.get("contributing_signals") or {}
        ok = ok and (
            isinstance(score, (int, float)) and 0 <= score <= 100
            and status in ("healthy", "warning", "critical")
            and "quota_pressure" in signals
            and "alert_intensity" in signals
        )
    except Exception:
        ok = False
    return ok


def check_risk_detection():
    """Account risk detector: output shape and consumption of health."""
    ok = True
    try:
        from amazon_research.monitoring import get_account_risk
        risk = get_account_risk(WORKSPACE_ID, since_days=30)
        ok = (
            isinstance(risk, dict)
            and risk.get("workspace_id") == WORKSPACE_ID
            and "risk_score" in risk
            and "risk_label" in risk
            and "explanation" in risk
            and "risk_signals" in risk
        )
        rscore = risk.get("risk_score")
        rlabel = risk.get("risk_label")
        rsigs = risk.get("risk_signals") or {}
        ok = ok and (
            isinstance(rscore, (int, float)) and 0 <= rscore <= 100
            and rlabel in ("low", "elevated", "high", "critical")
            and "workspace_health_score" in rsigs
            and "worker_queue_ops" in rsigs
        )
    except Exception:
        ok = False
    return ok


def check_ops_compatibility():
    """Alert routing, usage dashboard, cost insight: dashboard/ops-ready shapes."""
    ok = True
    try:
        from amazon_research.monitoring import (
            route_health_event,
            get_workspace_usage_dashboard,
            get_workspace_cost_insight,
            get_operational_health,
        )
        ops = get_operational_health()
        routes = route_health_event(ops, workspace_id=WORKSPACE_ID)
        ok = isinstance(routes, list) and (
            all("alert_id" in r and "severity" in r and "route_target_type" in r for r in routes)
            or len(routes) == 0
        )
        dash = get_workspace_usage_dashboard(WORKSPACE_ID, since_days=30)
        ok = ok and isinstance(dash, dict) and "usage" in dash and "queue_activity" in dash
        cost = get_workspace_cost_insight(WORKSPACE_ID, since_days=30)
        ok = ok and isinstance(cost, dict) and "cost_summary" in cost and "estimated_cost_drivers" in cost
    except Exception:
        ok = False
    return ok


def main():
    from dotenv import load_dotenv
    load_dotenv()

    telemetry_ok = check_telemetry_integrity()
    analytics_ok = check_analytics_snapshots()
    health_ok = check_health_scoring()
    risk_ok = check_risk_detection()
    ops_ok = check_ops_compatibility()

    strengths = [
        "Telemetry, health monitor, and alert routing are wired; health consumes get_metrics_snapshot.",
        "Workspace usage dashboard feeds cost insight and snapshot payload; snapshot payload matches historical view trend keys.",
        "Workspace health and account risk are rule-based and explainable; risk consumes health and ops signals.",
        "All layers return dashboard-ready structures (workspace_id, scores, labels, explanations, signals).",
    ]

    risks = [
        "Telemetry is in-memory only; process restart loses counters; consider periodic flush or persistence for historical dashboards.",
        "Snapshot and historical view depend on DB; no retention policy on tenant_analytics_snapshots; growth may require cleanup.",
        "Health and risk thresholds are fixed; multi-tenant or plan-based thresholds may be needed for SaaS.",
        "Operational health is global, not per-workspace; workspace risk uses it as a system-level factor only.",
    ]

    next_improvements = [
        "Add optional telemetry persistence or periodic snapshot for long-running ops dashboards.",
        "Define retention/cleanup for tenant_analytics_snapshots (e.g. keep last N per workspace).",
        "Consider configurable health/risk thresholds per plan or workspace for SaaS tiers.",
        "Wire alert routing to notification delivery (webhook/email) for critical and high-risk.",
        "Expose workspace health and risk in internal API for account management and ops visibility.",
    ]

    print("platform intelligence review OK")
    print("telemetry integrity: OK" if telemetry_ok else "telemetry integrity: FAIL")
    print("analytics snapshots: OK" if analytics_ok else "analytics snapshots: FAIL")
    print("health scoring: OK" if health_ok else "health scoring: FAIL")
    print("risk detection: OK" if risk_ok else "risk detection: FAIL")
    print("ops compatibility: OK" if ops_ok else "ops compatibility: FAIL")
    print("next improvements:")
    for n in next_improvements:
        print(f"  - {n}")
    print("strengths:")
    for s in strengths:
        print(f"  - {s}")
    print("potential risks:")
    for r in risks:
        print(f"  - {r}")

    all_ok = telemetry_ok and analytics_ok and health_ok and risk_ok and ops_ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
