"""
Step 200: Workspace isolation guards – require workspace context, validate resource scope.
Never crash callers; log pass/fail and cross-workspace blocked for audit.
"""
from typing import Any, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("workspace_isolation.guards")


def require_workspace_context(workspace_id: Optional[int], resource_type: str = "request") -> bool:
    """
    Require valid workspace context for a read or write. Returns True if workspace_id is valid, False otherwise.
    Logs isolation check pass or fail. Use at API/service entry for workspace-scoped operations.
    """
    if workspace_id is None:
        logger.warning(
            "workspace_isolation check fail resource_type=%s reason=missing_workspace_context",
            resource_type,
            extra={"resource_type": resource_type},
        )
        return False
    try:
        wid = int(workspace_id)
        if wid < 1:
            logger.warning(
                "workspace_isolation check fail resource_type=%s reason=invalid_workspace_id",
                resource_type,
                extra={"resource_type": resource_type},
            )
            return False
    except (TypeError, ValueError):
        logger.warning(
            "workspace_isolation check fail resource_type=%s reason=invalid_workspace_id",
            resource_type,
            extra={"resource_type": resource_type},
        )
        return False
    logger.debug(
        "workspace_isolation check pass resource_type=%s workspace_id=%s",
        resource_type,
        workspace_id,
        extra={"workspace_id": workspace_id, "resource_type": resource_type},
    )
    return True


def validate_resource_in_workspace(
    workspace_id: Optional[int],
    resource_workspace_id: Optional[int],
    resource_type: str = "resource",
    resource_id: Optional[Any] = None,
) -> bool:
    """
    Validate that a resource belongs to the requested workspace. Returns True if in scope, False otherwise.
    When False, logs cross-workspace access blocked (without leaking resource_workspace_id value).
    Use when you have a resource and need to ensure it belongs to the requesting workspace.
    """
    if workspace_id is None or resource_workspace_id is None:
        logger.warning(
            "workspace_isolation check fail resource_type=%s reason=missing_context",
            resource_type,
            extra={"resource_type": resource_type},
        )
        return False
    try:
        wid = int(workspace_id)
        rwid = int(resource_workspace_id)
    except (TypeError, ValueError):
        return False
    if wid != rwid:
        logger.warning(
            "workspace_isolation cross-workspace access blocked resource_type=%s workspace_id=%s",
            resource_type,
            workspace_id,
            extra={"workspace_id": workspace_id, "resource_type": resource_type},
        )
        return False
    logger.debug(
        "workspace_isolation check pass resource_type=%s workspace_id=%s",
        resource_type,
        workspace_id,
        extra={"workspace_id": workspace_id, "resource_type": resource_type},
    )
    return True


def safe_workspace_id(value: Any) -> Optional[int]:
    """Parse and validate workspace id for use in queries. Returns int or None. Does not log."""
    if value is None:
        return None
    try:
        wid = int(value)
        if wid < 1:
            return None
        return wid
    except (TypeError, ValueError):
        return None
