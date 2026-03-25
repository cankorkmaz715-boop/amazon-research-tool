"""
Step 133: Portfolio alert prioritization – rank alerts by importance.
Consumes portfolio watch, opportunity alerts, lifecycle, trend, operational signals.
Produces priority score, label (low/medium/high/critical), signal summary. Rule-based, explainable.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.alert_prioritization")

SOURCE_OPPORTUNITY_ALERT = "opportunity_alert"
SOURCE_PORTFOLIO_WATCH = "portfolio_watch"
SOURCE_LIFECYCLE = "lifecycle"
SOURCE_TREND = "trend"
SOURCE_OPERATIONAL = "operational"

LABEL_LOW = "low"
LABEL_MEDIUM = "medium"
LABEL_HIGH = "high"
LABEL_CRITICAL = "critical"


def _ts(x: Any) -> str:
    if x is None:
        return datetime.now(timezone.utc).isoformat()
    if hasattr(x, "isoformat"):
        return x.isoformat()
    return str(x)


def _priority_from_opportunity_alert(alert: Dict[str, Any]) -> tuple:
    """Return (score 0-100, label) for an opportunity alert."""
    atype = (alert.get("alert_type") or "").strip()
    signals = alert.get("triggering_signals") or {}
    score = 50.0
    if atype in ("demand_increase", "opportunity_increase", "new_strong_candidate"):
        score = 65.0
    elif atype in ("competition_drop", "trend_score_change"):
        score = 60.0
    demand_d = signals.get("demand_current")
    comp_d = signals.get("competition_current")
    if isinstance(demand_d, (int, float)) and demand_d >= 70:
        score += 10
    if isinstance(comp_d, (int, float)) and comp_d <= 35:
        score += 10
    score = min(100.0, score)
    if score >= 80:
        return score, LABEL_CRITICAL
    if score >= 65:
        return score, LABEL_HIGH
    if score >= 45:
        return score, LABEL_MEDIUM
    return score, LABEL_LOW


def _priority_from_watch_intelligence(alert: Dict[str, Any]) -> tuple:
    """Return (score, label) from watchlist intelligence output."""
    importance = alert.get("importance_score")
    if importance is not None:
        try:
            score = float(importance)
        except (TypeError, ValueError):
            score = 40.0
    else:
        score = 40.0
    label_raw = (alert.get("watch_intelligence_label") or "").strip()
    if label_raw == "high_priority":
        return max(score, 70.0), LABEL_HIGH if score < 85 else LABEL_CRITICAL
    if label_raw == "attention":
        return score, LABEL_HIGH if score >= 60 else LABEL_MEDIUM
    if label_raw == "stable":
        return min(score, 45.0), LABEL_MEDIUM if score >= 35 else LABEL_LOW
    return score, LABEL_MEDIUM if score >= 45 else LABEL_LOW


def _priority_from_operational(alert: Dict[str, Any]) -> tuple:
    """Return (score, label) from operational/routing event (severity)."""
    severity = (alert.get("severity") or "").strip().lower()
    if severity == "critical":
        return 90.0, LABEL_CRITICAL
    if severity == "warning":
        return 70.0, LABEL_HIGH
    return 50.0, LABEL_MEDIUM


def prioritize_alert(
    alert: Dict[str, Any],
    alert_source: str,
    *,
    alert_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Prioritize a single alert. alert: raw alert dict; alert_source: opportunity_alert | portfolio_watch |
    lifecycle | trend | operational. Returns: alert_id, alert_source, priority_score, priority_label,
    signal_summary, timestamp.
    """
    out: Dict[str, Any] = {
        "alert_id": alert_id or str(alert.get("id") or alert.get("watch_id") or ""),
        "alert_source": (alert_source or "").strip() or SOURCE_OPPORTUNITY_ALERT,
        "priority_score": 50.0,
        "priority_label": LABEL_MEDIUM,
        "signal_summary": {},
        "timestamp": _ts(alert.get("recorded_at") or alert.get("timestamp")),
    }
    if not out["alert_id"]:
        out["alert_id"] = str(id(alert))
    source = out["alert_source"]
    if source == SOURCE_OPPORTUNITY_ALERT:
        score, label = _priority_from_opportunity_alert(alert)
        out["priority_score"] = round(score, 1)
        out["priority_label"] = label
        out["signal_summary"] = {
            "alert_type": alert.get("alert_type"),
            "target_entity": alert.get("target_entity"),
            "triggering_signals": alert.get("triggering_signals") or {},
        }
    elif source == SOURCE_PORTFOLIO_WATCH:
        score, label = _priority_from_watch_intelligence(alert)
        out["priority_score"] = round(score, 1)
        out["priority_label"] = label
        out["signal_summary"] = {
            "watched_entity": alert.get("watched_entity"),
            "importance_score": alert.get("importance_score"),
            "detected_change_summary": alert.get("detected_change_summary"),
        }
    elif source == SOURCE_OPERATIONAL:
        score, label = _priority_from_operational(alert)
        out["priority_score"] = round(score, 1)
        out["priority_label"] = label
        out["signal_summary"] = {
            "severity": alert.get("severity"),
            "route_reason": alert.get("route_reason"),
        }
    else:
        # lifecycle, trend, or unknown: generic scoring
        out["signal_summary"] = dict(alert)
        out["priority_score"] = 50.0
        out["priority_label"] = LABEL_MEDIUM
    return out


def get_prioritized_alerts(
    workspace_id: Optional[int] = None,
    *,
    limit_opportunity: int = 30,
    limit_watch: int = 20,
    include_operational: bool = False,
) -> List[Dict[str, Any]]:
    """
    Aggregate alerts from opportunity_alerts and watchlist intelligence, optionally operational,
    then prioritize and sort by priority_score descending. Returns list of prioritized alert outputs.
    """
    combined: List[tuple] = []
    try:
        from amazon_research.db import list_opportunity_alerts
        opp_alerts = list_opportunity_alerts(limit=limit_opportunity, workspace_id=workspace_id)
        for a in opp_alerts:
            combined.append((a, SOURCE_OPPORTUNITY_ALERT))
    except Exception as e:
        logger.debug("get_prioritized_alerts list_opportunity_alerts failed: %s", e)
    if workspace_id is not None:
        try:
            from amazon_research.discovery import list_watch_intelligence
            watch_list = list_watch_intelligence(workspace_id, limit=limit_watch)
            for w in watch_list:
                # Treat high_priority and attention as "alerts" for prioritization
                if (w.get("watch_intelligence_label") or "") in ("high_priority", "attention", "stable"):
                    combined.append((w, SOURCE_PORTFOLIO_WATCH))
        except Exception as e:
            logger.debug("get_prioritized_alerts list_watch_intelligence failed: %s", e)
    if include_operational:
        try:
            from amazon_research.monitoring import get_operational_health, route_health_event
            health = get_operational_health()
            routes = route_health_event(health, workspace_id=workspace_id)
            for r in routes:
                combined.append((r, SOURCE_OPERATIONAL))
        except Exception as e:
            logger.debug("get_prioritized_alerts operational failed: %s", e)
    results: List[Dict[str, Any]] = []
    for alert, source in combined:
        aid = alert.get("id") or alert.get("watch_id") or alert.get("alert_id")
        results.append(prioritize_alert(alert, source, alert_id=str(aid) if aid is not None else None))
    results.sort(key=lambda x: (-(x.get("priority_score") or 0), _ts(x.get("timestamp", ""))))
    return results
