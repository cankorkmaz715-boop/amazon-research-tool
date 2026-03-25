"""
Step 200: Workspace isolation validation – workspace-scoped access pattern and resource types.
All workspace-owned resources must be read/written with workspace_id; no id-only cross-workspace access.
"""
from typing import Any, Dict, Optional

# Resource types used in guards and logging
RESOURCE_INTELLIGENCE_SUMMARY = "intelligence_summary"
RESOURCE_SNAPSHOT = "snapshot"
RESOURCE_CACHE = "cache"
RESOURCE_CONFIGURATION = "configuration"
RESOURCE_PORTFOLIO = "portfolio"
RESOURCE_ALERT_PREFERENCES = "alert_preferences"
RESOURCE_ACTIVITY_LOG = "activity_log"

WORKSPACE_SCOPED_RESOURCE_TYPES = frozenset({
    RESOURCE_INTELLIGENCE_SUMMARY,
    RESOURCE_SNAPSHOT,
    RESOURCE_CACHE,
    RESOURCE_CONFIGURATION,
    RESOURCE_PORTFOLIO,
    RESOURCE_ALERT_PREFERENCES,
    RESOURCE_ACTIVITY_LOG,
})


def ensure_workspace_scope_for_response(
    workspace_id: Optional[int],
    resource: Optional[Dict[str, Any]],
    resource_type: str,
) -> bool:
    """
    When returning a single resource from a workspace-scoped API, ensure resource.workspace_id == workspace_id.
    Returns True if in scope or resource is None/empty; False if cross-workspace (caller should return 403/404).
    Does not leak resource workspace_id in logs.
    """
    if workspace_id is None:
        return False
    if not resource or not isinstance(resource, dict):
        return True
    rwid = resource.get("workspace_id")
    if rwid is None:
        return True
    try:
        if int(workspace_id) != int(rwid):
            return False
    except (TypeError, ValueError):
        return False
    return True
