"""
Step 237: Live opportunity stream & runtime feed refresh – types and constants.
"""
from typing import Any, Dict

# Cycle name for scheduler integration
CYCLE_OPPORTUNITY_FEED_REFRESH = "opportunity_feed_refresh"

# Default interval (seconds) for feed refresh cycle
DEFAULT_FEED_REFRESH_INTERVAL_SECONDS = 1800.0  # 30 min

# Max workspaces to refresh per cycle (safety cap)
MAX_WORKSPACES_PER_REFRESH = 100


def refresh_result(workspace_id: int, count: int, error: str = None) -> Dict[str, Any]:
    """Stable result shape for a single workspace refresh."""
    return {
        "workspace_id": workspace_id,
        "opportunity_count": count,
        "error": error,
    }
