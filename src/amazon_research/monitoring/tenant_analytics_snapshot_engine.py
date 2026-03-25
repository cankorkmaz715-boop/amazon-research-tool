"""
Step 116: Tenant analytics snapshot engine – create periodic workspace-level analytics summaries.
Aggregates usage dashboard, cost insight, quota, alerts. History-friendly storage.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.tenant_analytics_snapshot_engine")


def build_tenant_snapshot_payload(
    workspace_id: int,
    since_days: Optional[int] = 30,
) -> Dict[str, Any]:
    """
    Build a snapshot payload from usage dashboard and cost insight. Returns dict with:
    usage_summary, quota_status, cost_insight_summary, alert_volume, discovery_activity,
    refresh_activity, opportunity_generation_volume, snapshot_at, since_days.
    """
    payload: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "since_days": since_days,
        "usage_summary": {},
        "quota_status": {},
        "cost_insight_summary": {},
        "alert_volume": 0,
        "discovery_activity": 0,
        "refresh_activity": 0,
        "opportunity_generation_volume": 0,
    }

    try:
        from amazon_research.monitoring import get_workspace_usage_dashboard
        dash = get_workspace_usage_dashboard(workspace_id, since_days=since_days)
    except Exception as e:
        logger.debug("build_tenant_snapshot dashboard failed: %s", e)
        dash = {}

    usage = dash.get("usage") or {}
    payload["usage_summary"] = dict(usage)
    payload["quota_status"] = dict(dash.get("quota_consumption") or {})
    payload["alert_volume"] = int(dash.get("alert_count") or 0)
    payload["discovery_activity"] = int(usage.get("discovery_run") or 0)
    payload["refresh_activity"] = int(usage.get("refresh_run") or 0)
    payload["opportunity_generation_volume"] = int(dash.get("alert_count") or 0)

    try:
        from amazon_research.monitoring import get_workspace_cost_insight
        insight = get_workspace_cost_insight(workspace_id, since_days=since_days)
        payload["cost_insight_summary"] = dict(insight.get("cost_summary") or {})
    except Exception as e:
        logger.debug("build_tenant_snapshot cost_insight failed: %s", e)

    return payload


def create_and_store_snapshot(
    workspace_id: int,
    since_days: Optional[int] = 30,
) -> Optional[int]:
    """
    Build snapshot payload and persist it. Returns snapshot id or None.
    """
    payload = build_tenant_snapshot_payload(workspace_id, since_days=since_days)
    try:
        from amazon_research.db.tenant_analytics_snapshots import save_tenant_snapshot
        return save_tenant_snapshot(
            workspace_id,
            payload,
            since_days=since_days,
        )
    except Exception as e:
        logger.debug("create_and_store_snapshot save failed: %s", e)
        return None
