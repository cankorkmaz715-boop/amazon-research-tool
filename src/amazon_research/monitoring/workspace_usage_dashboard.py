"""
Step 114: Workspace usage dashboard metrics – aggregate per-workspace operational usage.
Dashboard-ready outputs: discovery, refresh, scoring, export, quota consumption, alert counts, queue activity.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.workspace_usage_dashboard")


def get_workspace_usage_dashboard(
    workspace_id: int,
    since_days: Optional[int] = 30,
) -> Dict[str, Any]:
    """
    Aggregate per-workspace usage for dashboard. Returns structured output:
    usage (event_type -> count), quota_consumption (quota_type -> { limit, used, remaining }),
    rate_limit_events (placeholder), alert_count, queue_activity (job counts), workspace_id, since_days.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "since_days": since_days,
        "usage": {},
        "quota_consumption": {},
        "rate_limit_events": {},
        "alert_count": 0,
        "queue_activity": {},
    }

    try:
        from amazon_research.db import get_usage_summary_for_workspace
        out["usage"] = get_usage_summary_for_workspace(workspace_id, since_days=since_days)
    except Exception as e:
        logger.debug("get_usage_summary_for_workspace failed: %s", e)

    try:
        from amazon_research.db import list_workspace_quotas, get_usage_summary_for_workspace
        usage = out.get("usage") or get_usage_summary_for_workspace(workspace_id, since_days=since_days)
        quotas = list_workspace_quotas(workspace_id)
        for q in quotas or []:
            qtype = (q.get("quota_type") or "").strip()
            if not qtype:
                continue
            limit = q.get("limit_value")
            period_days = q.get("period_days") or 30
            used = usage.get(qtype, 0) if usage else 0
            remaining = (limit - used) if isinstance(limit, (int, float)) else None
            out["quota_consumption"][qtype] = {
                "limit": limit,
                "used": used,
                "remaining": remaining,
                "period_days": period_days,
            }
    except Exception as e:
        logger.debug("quota_consumption aggregation failed: %s", e)

    # Rate-limit events: in-memory only; placeholder for future persistence
    out["rate_limit_events"] = {}

    try:
        from amazon_research.db.opportunity_alerts import list_opportunity_alerts
        alerts = list_opportunity_alerts(workspace_id=workspace_id, limit=2000)
        out["alert_count"] = len(alerts) if alerts else 0
    except Exception as e:
        logger.debug("alert_count failed: %s", e)

    try:
        from amazon_research.db import get_job_counts_for_workspace
        out["queue_activity"] = get_job_counts_for_workspace(workspace_id, since_days=since_days)
    except Exception as e:
        logger.debug("queue_activity failed: %s", e)
        out["queue_activity"] = {"pending": 0, "completed": 0, "failed": 0, "running": 0, "total": 0}

    return out


def get_all_workspaces_usage_summary(
    since_days: Optional[int] = 30,
) -> List[Dict[str, Any]]:
    """
    Return a list of per-workspace summary records for ops visibility.
    Each item: workspace_id, usage (event_type -> count), alert_count, queue_activity summary.
    """
    result: List[Dict[str, Any]] = []
    try:
        from amazon_research.db import (
            get_job_counts_for_workspace,
            get_usage_summary_for_workspace,
            list_workspaces,
        )
        from amazon_research.db.opportunity_alerts import list_opportunity_alerts
        workspaces = list_workspaces() or []
        for ws in workspaces:
            wid = ws.get("id")
            if wid is None:
                continue
            try:
                usage = get_usage_summary_for_workspace(wid, since_days=since_days)
                alerts = list_opportunity_alerts(workspace_id=wid, limit=500)
                job_counts = get_job_counts_for_workspace(wid, since_days=since_days)
                result.append({
                    "workspace_id": wid,
                    "usage": usage,
                    "alert_count": len(alerts) if alerts else 0,
                    "queue_activity": job_counts,
                })
            except Exception as e:
                logger.debug("workspace %s summary failed: %s", wid, e)
    except Exception as e:
        logger.debug("get_all_workspaces_usage_summary failed: %s", e)
    return result
