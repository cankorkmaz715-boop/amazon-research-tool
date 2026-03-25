"""
Step 115: Workspace cost insight layer – estimate workspace-level operational cost drivers.
Lightweight, approximate. Uses usage dashboard, telemetry, job activity. Dashboard-ready outputs.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.workspace_cost_insight")

# Approximate pages per run for bandwidth attribution (no per-workspace telemetry)
EST_PAGES_DISCOVERY = 5
EST_PAGES_REFRESH = 2
EST_BYTES_PER_PAGE = 500_000

COST_LEVEL_LOW = "low"
COST_LEVEL_MEDIUM = "medium"
COST_LEVEL_HIGH = "high"

HEAVY_USAGE_THRESHOLD = 10


def get_workspace_cost_insight(
    workspace_id: int,
    since_days: Optional[int] = 30,
) -> Dict[str, Any]:
    """
    Estimate workspace-level cost drivers from usage and queue activity. Returns:
    workspace_id, since_days, estimated_cost_drivers, heavy_usage_areas, cost_summary,
    bandwidth_attribution (estimated pages/bytes from usage), job cost visibility.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "since_days": since_days,
        "estimated_cost_drivers": {},
        "heavy_usage_areas": [],
        "cost_summary": {},
        "bandwidth_attribution": {},
        "job_cost_visibility": {},
    }

    try:
        from amazon_research.monitoring import get_workspace_usage_dashboard
        dash = get_workspace_usage_dashboard(workspace_id, since_days=since_days)
    except Exception as e:
        logger.debug("get_workspace_cost_insight dashboard failed: %s", e)
        dash = {}

    usage = dash.get("usage") or {}
    queue_activity = dash.get("queue_activity") or {}
    alert_count = dash.get("alert_count") or 0

    discovery = int(usage.get("discovery_run") or 0)
    refresh = int(usage.get("refresh_run") or 0)
    scoring = int(usage.get("scoring_run") or 0)
    export_csv = int(usage.get("export_csv") or 0)
    export_json = int(usage.get("export_json") or 0)
    export_total = export_csv + export_json
    completed = int(queue_activity.get("completed") or 0)
    failed = int(queue_activity.get("failed") or 0)
    job_total = completed + failed

    drivers = {
        "discovery": discovery,
        "refresh": refresh,
        "scoring": scoring,
        "export": export_total,
        "jobs_completed": completed,
        "jobs_failed": failed,
        "alerts": int(alert_count),
    }
    out["estimated_cost_drivers"] = drivers

    # Heavy usage areas: drivers above threshold, sorted by count descending
    heavy = [k for k, v in drivers.items() if v >= HEAVY_USAGE_THRESHOLD]
    heavy.sort(key=lambda k: drivers[k], reverse=True)
    if not heavy:
        top = sorted(drivers.keys(), key=lambda k: drivers[k], reverse=True)[:3]
        heavy = [k for k in top if drivers[k] > 0]
    out["heavy_usage_areas"] = heavy

    # Simple cost summary: total estimated units, level
    total_units = sum(drivers.values())
    if total_units <= 20:
        level = COST_LEVEL_LOW
    elif total_units <= 100:
        level = COST_LEVEL_MEDIUM
    else:
        level = COST_LEVEL_HIGH
    out["cost_summary"] = {
        "total_estimated_units": total_units,
        "level": level,
        "breakdown": drivers,
    }

    # Bandwidth attribution: estimated from usage (no per-workspace telemetry)
    estimated_pages = (
        discovery * EST_PAGES_DISCOVERY
        + refresh * EST_PAGES_REFRESH
    )
    estimated_bytes = estimated_pages * EST_BYTES_PER_PAGE
    out["bandwidth_attribution"] = {
        "estimated_pages": estimated_pages,
        "estimated_bytes": estimated_bytes,
        "estimated_mb": round(estimated_bytes / (1024 * 1024), 2),
        "by_driver": {
            "discovery": discovery * EST_PAGES_DISCOVERY,
            "refresh": refresh * EST_PAGES_REFRESH,
        },
    }

    # Job cost visibility: queue activity as cost signal
    out["job_cost_visibility"] = {
        "completed": completed,
        "failed": failed,
        "total_processed": job_total,
        "pending": int(queue_activity.get("pending") or 0),
        "running": int(queue_activity.get("running") or 0),
    }

    return out


def get_all_workspaces_cost_insight(
    since_days: Optional[int] = 30,
) -> List[Dict[str, Any]]:
    """Return cost insight for all workspaces (ops visibility, future billing dashboards)."""
    result: List[Dict[str, Any]] = []
    try:
        from amazon_research.db import list_workspaces
        workspaces = list_workspaces() or []
        for ws in workspaces:
            wid = ws.get("id")
            if wid is None:
                continue
            try:
                result.append(get_workspace_cost_insight(wid, since_days=since_days))
            except Exception as e:
                logger.debug("cost_insight workspace %s failed: %s", wid, e)
    except Exception as e:
        logger.debug("get_all_workspaces_cost_insight failed: %s", e)
    return result
