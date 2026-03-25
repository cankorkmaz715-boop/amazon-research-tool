"""
Step 117: Historical workspace analytics view – trend layer on top of tenant analytics snapshots.
Read-focused; dashboard-ready. Usage, quota pressure, cost, alert, discovery, refresh, opportunity trends.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.historical_workspace_analytics")


def _ts(dt: Any) -> str:
    """Serialize snapshot_at for dashboard (ISO string)."""
    if dt is None:
        return ""
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _usage_total(payload: Dict[str, Any]) -> float:
    """Sum of all usage_summary counts for a single scalar trend value."""
    usage = payload.get("usage_summary") or {}
    if not isinstance(usage, dict):
        return 0.0
    try:
        return float(sum(v for v in usage.values() if isinstance(v, (int, float))))
    except (TypeError, ValueError):
        return 0.0


def _quota_pressure(payload: Dict[str, Any]) -> float:
    """Single pressure value: max(used/limit) across quotas, 0 when no limits."""
    status = payload.get("quota_status") or {}
    if not isinstance(status, dict):
        return 0.0
    pressure = 0.0
    for qv in status.values():
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


def get_historical_workspace_analytics(
    workspace_id: int,
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Build historical analytics view from snapshot history. Returns dashboard-ready output:
    workspace_id, trends (usage_trend, quota_pressure_trend, cost_trend, alert_volume_trend,
    discovery_activity_trend, refresh_activity_trend, opportunity_generation_trend),
    snapshots_used. Each trend is a list of { snapshot_at, value } oldest-first for charting.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "trends": {
            "usage_trend": [],
            "quota_pressure_trend": [],
            "cost_trend": [],
            "alert_volume_trend": [],
            "discovery_activity_trend": [],
            "refresh_activity_trend": [],
            "opportunity_generation_trend": [],
        },
        "snapshots_used": 0,
    }

    try:
        from amazon_research.db import get_snapshot_history
        history = get_snapshot_history(workspace_id, limit=limit)
    except Exception as e:
        logger.debug("get_historical_workspace_analytics get_snapshot_history failed: %s", e)
        return out

    if not history:
        return out

    # Chronological order (oldest first) for trend series
    ordered = list(reversed(history))
    out["snapshots_used"] = len(ordered)

    for snap in ordered:
        snapshot_at = snap.get("snapshot_at")
        payload = snap.get("payload") or {}
        ts = _ts(snapshot_at)

        out["trends"]["usage_trend"].append({"snapshot_at": ts, "value": _usage_total(payload)})
        out["trends"]["quota_pressure_trend"].append({"snapshot_at": ts, "value": _quota_pressure(payload)})

        cost_summary = payload.get("cost_insight_summary") or {}
        cost_val = cost_summary.get("total_estimated_units")
        if cost_val is None:
            cost_val = 0.0
        try:
            cost_val = float(cost_val)
        except (TypeError, ValueError):
            cost_val = 0.0
        out["trends"]["cost_trend"].append({"snapshot_at": ts, "value": cost_val})

        out["trends"]["alert_volume_trend"].append({
            "snapshot_at": ts,
            "value": int(payload.get("alert_volume") or 0),
        })
        out["trends"]["discovery_activity_trend"].append({
            "snapshot_at": ts,
            "value": int(payload.get("discovery_activity") or 0),
        })
        out["trends"]["refresh_activity_trend"].append({
            "snapshot_at": ts,
            "value": int(payload.get("refresh_activity") or 0),
        })
        out["trends"]["opportunity_generation_trend"].append({
            "snapshot_at": ts,
            "value": int(payload.get("opportunity_generation_volume") or 0),
        })

    return out
