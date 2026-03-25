"""
Step 200: Multi-workspace isolation – guards, validation, and workspace-scoped access pattern.
All workspace-owned resources (intelligence, snapshots, cache, configuration, portfolio,
alert preferences, activity log) must be accessed with workspace context; writes must verify scope.
"""
from .guards import (
    require_workspace_context,
    validate_resource_in_workspace,
    safe_workspace_id,
)
from .validation import (
    ensure_workspace_scope_for_response,
    RESOURCE_INTELLIGENCE_SUMMARY,
    RESOURCE_SNAPSHOT,
    RESOURCE_CACHE,
    RESOURCE_CONFIGURATION,
    RESOURCE_PORTFOLIO,
    RESOURCE_ALERT_PREFERENCES,
    RESOURCE_ACTIVITY_LOG,
    WORKSPACE_SCOPED_RESOURCE_TYPES,
)

__all__ = [
    "require_workspace_context",
    "validate_resource_in_workspace",
    "safe_workspace_id",
    "ensure_workspace_scope_for_response",
    "RESOURCE_INTELLIGENCE_SUMMARY",
    "RESOURCE_SNAPSHOT",
    "RESOURCE_CACHE",
    "RESOURCE_CONFIGURATION",
    "RESOURCE_PORTFOLIO",
    "RESOURCE_ALERT_PREFERENCES",
    "RESOURCE_ACTIVITY_LOG",
    "WORKSPACE_SCOPED_RESOURCE_TYPES",
]
