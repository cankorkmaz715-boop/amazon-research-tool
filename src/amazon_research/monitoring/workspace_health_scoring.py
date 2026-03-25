"""
Step 118: Workspace health scoring – evaluate workspace using analytics and operational signals.
Rule-based, explainable. Usage stability, quota pressure, alert intensity, cost pressure, activity balance.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.workspace_health_scoring")

HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_WARNING = "warning"
HEALTH_STATUS_CRITICAL = "critical"

SCORE_HEALTHY_MIN = 70
SCORE_WARNING_MIN = 40


def _quota_pressure_from_dashboard(quota_consumption: Dict[str, Any]) -> float:
    """Max used/limit across quotas; 0 when no limits."""
    pressure = 0.0
    for qv in (quota_consumption or {}).values():
        if not isinstance(qv, dict):
            continue
        limit = qv.get("limit")
        used = qv.get("used")
        if limit is not None and used is not None and limit > 0:
            try:
                p = float(used) / float(limit)
                pressure = max(pressure, min(1.0, p))
            except (TypeError, ValueError):
                pass
    return round(pressure, 4)


def _usage_stability_from_history(workspace_id: int, limit: int = 10) -> str:
    """Stable if 2+ snapshots and usage_trend has low variance; else unknown or unstable."""
    try:
        from amazon_research.monitoring import get_historical_workspace_analytics
        view = get_historical_workspace_analytics(workspace_id, limit=limit)
        points = (view.get("trends") or {}).get("usage_trend") or []
        if len(points) < 2:
            return "unknown"
        values = [p.get("value") for p in points if isinstance(p.get("value"), (int, float))]
        if len(values) < 2:
            return "unknown"
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        if mean_val > 0 and (variance / mean_val) > 2.0:
            return "unstable"
        return "stable"
    except Exception:
        return "unknown"


def get_workspace_health(
    workspace_id: int,
    since_days: Optional[int] = 30,
) -> Dict[str, Any]:
    """
    Evaluate workspace health from usage dashboard, cost insight, optional history and ops health.
    Returns: workspace_id, health_score (0-100), health_status (healthy|warning|critical),
    explanation (compact string), contributing_signals (dict).
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "health_score": 100,
        "health_status": HEALTH_STATUS_HEALTHY,
        "explanation": "",
        "contributing_signals": {},
    }

    try:
        from amazon_research.monitoring import get_workspace_usage_dashboard
        dash = get_workspace_usage_dashboard(workspace_id, since_days=since_days)
    except Exception as e:
        logger.debug("get_workspace_health dashboard failed: %s", e)
        dash = {}

    try:
        from amazon_research.monitoring import get_workspace_cost_insight
        insight = get_workspace_cost_insight(workspace_id, since_days=since_days)
    except Exception as e:
        logger.debug("get_workspace_health cost_insight failed: %s", e)
        insight = {}

    quota_consumption = dash.get("quota_consumption") or {}
    usage = dash.get("usage") or {}
    alert_count = int(dash.get("alert_count") or 0)
    discovery = int(usage.get("discovery_run") or 0)
    refresh = int(usage.get("refresh_run") or 0)
    cost_summary = insight.get("cost_summary") or {}
    cost_level = (cost_summary.get("level") or "low").strip().lower()

    # Contributing signals
    quota_pressure = _quota_pressure_from_dashboard(quota_consumption)
    usage_stability = _usage_stability_from_history(workspace_id)
    activity_total = discovery + refresh
    activity_balance = "balanced" if (discovery > 0 and refresh > 0) else ("inactive" if activity_total == 0 else "imbalanced")

    out["contributing_signals"] = {
        "quota_pressure": quota_pressure,
        "alert_intensity": alert_count,
        "cost_pressure": cost_level,
        "usage_stability": usage_stability,
        "activity_balance": activity_balance,
        "discovery_activity": discovery,
        "refresh_activity": refresh,
    }

    # Rule-based score: start 100, deduct for pressure
    score = 100.0
    reasons: List[str] = []

    if quota_pressure >= 0.9:
        score -= 35
        reasons.append("quota pressure critical")
    elif quota_pressure >= 0.7:
        score -= 20
        reasons.append("quota pressure high")
    elif quota_pressure >= 0.5:
        score -= 10
        reasons.append("quota pressure moderate")

    if cost_level == "high":
        score -= 15
        reasons.append("cost pressure high")
    elif cost_level == "medium":
        score -= 5
        reasons.append("cost pressure moderate")

    if alert_count > 50:
        score -= 10
        reasons.append("alert intensity high")
    elif alert_count > 20:
        score -= 5
        reasons.append("alert intensity elevated")

    if usage_stability == "unstable":
        score -= 10
        reasons.append("usage unstable")

    if activity_balance == "inactive" and (discovery + refresh) == 0:
        score -= 5
        reasons.append("no discovery/refresh activity")

    try:
        from amazon_research.monitoring import get_operational_health
        ops = get_operational_health()
        if (ops.get("overall") or "").strip() == "critical":
            score -= 15
            reasons.append("operational health critical")
        elif (ops.get("overall") or "").strip() == "warning":
            score -= 5
            reasons.append("operational health warning")
    except Exception:
        pass

    score = max(0.0, min(100.0, score))
    out["health_score"] = round(score, 1)

    if score >= SCORE_HEALTHY_MIN:
        out["health_status"] = HEALTH_STATUS_HEALTHY
    elif score >= SCORE_WARNING_MIN:
        out["health_status"] = HEALTH_STATUS_WARNING
    else:
        out["health_status"] = HEALTH_STATUS_CRITICAL

    out["explanation"] = "; ".join(reasons) if reasons else "no significant issues"

    return out
