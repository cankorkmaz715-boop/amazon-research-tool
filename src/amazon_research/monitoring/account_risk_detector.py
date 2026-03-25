"""
Step 119: Account/workspace risk detector – evaluate workspace risk from health and analytics signals.
Rule-based, explainable. Reuses workspace health, ops health, historical analytics.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.account_risk_detector")

RISK_LABEL_LOW = "low"
RISK_LABEL_ELEVATED = "elevated"
RISK_LABEL_HIGH = "high"
RISK_LABEL_CRITICAL = "critical"

RISK_THRESHOLD_LOW = 25
RISK_THRESHOLD_ELEVATED = 50
RISK_THRESHOLD_HIGH = 75


def _cost_anomaly_from_history(workspace_id: int, limit: int = 10) -> str:
    """Simple cost anomaly: spike if latest cost_trend >> mean of previous. Else normal/unknown."""
    try:
        from amazon_research.monitoring import get_historical_workspace_analytics
        view = get_historical_workspace_analytics(workspace_id, limit=limit)
        points = (view.get("trends") or {}).get("cost_trend") or []
        if len(points) < 3:
            return "unknown"
        values = [p.get("value") for p in points if isinstance(p.get("value"), (int, float))]
        if len(values) < 3:
            return "unknown"
        recent = values[0]
        prev_mean = sum(values[1:]) / (len(values) - 1)
        if prev_mean > 0 and recent > prev_mean * 2.0:
            return "spike"
        return "normal"
    except Exception:
        return "unknown"


def get_account_risk(
    workspace_id: int,
    since_days: Optional[int] = 30,
) -> Dict[str, Any]:
    """
    Evaluate workspace/account risk from health score, alert intensity, quota pressure,
    cost anomalies, worker/queue health, discovery/refresh imbalance, operational state.
    Returns: workspace_id, risk_score (0-100, higher = more risk), risk_label (low|elevated|high|critical),
    explanation (compact string), risk_signals (dict).
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "risk_score": 0.0,
        "risk_label": RISK_LABEL_LOW,
        "explanation": "",
        "risk_signals": {},
    }

    try:
        from amazon_research.monitoring import get_workspace_health
        health = get_workspace_health(workspace_id, since_days=since_days)
    except Exception as e:
        logger.debug("get_account_risk get_workspace_health failed: %s", e)
        health = {}

    signals = health.get("contributing_signals") or {}
    health_score = float(health.get("health_score") or 100)
    health_status = (health.get("health_status") or "healthy").strip().lower()
    quota_pressure = float(signals.get("quota_pressure") or 0)
    alert_intensity = int(signals.get("alert_intensity") or 0)
    cost_pressure = (signals.get("cost_pressure") or "low").strip().lower()
    activity_balance = (signals.get("activity_balance") or "unknown").strip().lower()
    usage_stability = (signals.get("usage_stability") or "unknown").strip().lower()

    cost_anomaly = _cost_anomaly_from_history(workspace_id)
    ops_overall = "healthy"
    try:
        from amazon_research.monitoring import get_operational_health
        ops = get_operational_health()
        ops_overall = (ops.get("overall") or "healthy").strip().lower()
    except Exception:
        pass

    out["risk_signals"] = {
        "workspace_health_score": health_score,
        "workspace_health_status": health_status,
        "alert_intensity": alert_intensity,
        "quota_pressure": quota_pressure,
        "cost_pressure": cost_pressure,
        "cost_anomaly": cost_anomaly,
        "worker_queue_ops": ops_overall,
        "discovery_refresh_balance": activity_balance,
        "usage_stability": usage_stability,
    }

    # Rule-based risk score: 0-100, higher = more risk
    score = 0.0
    reasons: List[str] = []

    if health_status == "critical":
        score += 40
        reasons.append("workspace health critical")
    elif health_status == "warning":
        score += 20
        reasons.append("workspace health warning")

    score += quota_pressure * 25
    if quota_pressure >= 0.7:
        reasons.append("quota pressure high")

    if alert_intensity > 50:
        score += 15
        reasons.append("alert intensity high")
    elif alert_intensity > 20:
        score += 8
        reasons.append("alert intensity elevated")

    if cost_pressure == "high":
        score += 15
        reasons.append("cost pressure high")
    elif cost_pressure == "medium":
        score += 5

    if cost_anomaly == "spike":
        score += 15
        reasons.append("cost anomaly spike")

    if ops_overall == "critical":
        score += 20
        reasons.append("worker/queue health critical")
    elif ops_overall == "warning":
        score += 10
        reasons.append("worker/queue health warning")

    if activity_balance == "imbalanced":
        score += 5
        reasons.append("discovery/refresh imbalance")
    elif activity_balance == "inactive":
        score += 3

    if usage_stability == "unstable":
        score += 10
        reasons.append("usage unstable")

    score = min(100.0, max(0.0, score))
    out["risk_score"] = round(score, 1)

    if score >= RISK_THRESHOLD_HIGH:
        out["risk_label"] = RISK_LABEL_CRITICAL
    elif score >= RISK_THRESHOLD_ELEVATED:
        out["risk_label"] = RISK_LABEL_HIGH
    elif score >= RISK_THRESHOLD_LOW:
        out["risk_label"] = RISK_LABEL_ELEVATED
    else:
        out["risk_label"] = RISK_LABEL_LOW

    out["explanation"] = "; ".join(reasons) if reasons else "no significant risk signals"

    return out
