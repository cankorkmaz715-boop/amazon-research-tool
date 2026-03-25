"""
Step 199: Workspace activity log – structured workspace events for debugging, audit, dashboard timeline.
All create paths are non-blocking: never raise to callers.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("workspace_activity_log")


def create_workspace_activity_event(
    workspace_id: Optional[int],
    event_type: str,
    event_label: Optional[str] = None,
    actor_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    source_module: Optional[str] = None,
    event_payload: Optional[Dict[str, Any]] = None,
    severity: str = "info",
) -> Optional[int]:
    """
    Append one activity event. Non-blocking: on failure logs warning and returns None; never raises.
    Use for configuration_updated, portfolio_item_added, alert_preferences_updated, intelligence_refresh, etc.
    """
    if workspace_id is None:
        return None
    try:
        from amazon_research.db.workspace_activity_log import create_workspace_activity_event as db_create
        return db_create(
            workspace_id=workspace_id,
            event_type=event_type or "configuration_updated",
            event_label=event_label,
            actor_type=actor_type,
            actor_id=actor_id,
            source_module=source_module,
            event_payload=event_payload,
            severity=severity or "info",
        )
    except Exception as e:
        logger.warning("workspace_activity_log skipped (non-blocking) workspace_id=%s event_type=%s: %s", workspace_id, event_type, e)
        return None


def list_workspace_activity_events(
    workspace_id: Optional[int],
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List recent activity events. Returns [] when workspace_id is None or on error."""
    if workspace_id is None:
        return []
    try:
        from amazon_research.db.workspace_activity_log import list_workspace_activity_events as db_list
        return db_list(workspace_id, event_type=event_type, severity=severity, limit=limit)
    except Exception as e:
        logger.warning("workspace_activity_log list failed workspace_id=%s: %s", workspace_id, e)
        return []


def get_workspace_activity_summary(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Summary counts by event_type and severity. Stable shape; never returns None."""
    if workspace_id is None:
        return {"workspace_id": None, "total": 0, "by_event_type": {}, "by_severity": {"info": 0, "warning": 0, "error": 0}}
    try:
        from amazon_research.db.workspace_activity_log import get_workspace_activity_summary as db_summary
        return db_summary(workspace_id)
    except Exception as e:
        logger.warning("workspace_activity_log summary failed workspace_id=%s: %s", workspace_id, e)
        return {"workspace_id": workspace_id, "total": 0, "by_event_type": {}, "by_severity": {"info": 0, "warning": 0, "error": 0}}
