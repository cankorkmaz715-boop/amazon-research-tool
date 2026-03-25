"""
Step 194: Workspace intelligence cache keys – stable key format for in-memory cache.
"""
from typing import Optional

CACHE_KEY_PREFIX = "wi:summary"


def workspace_intelligence_cache_key(workspace_id: Optional[int]) -> Optional[str]:
    """Return cache key for workspace intelligence summary. None if workspace_id invalid."""
    if workspace_id is None:
        return None
    try:
        wid = int(workspace_id)
        if wid < 1:
            return None
        return f"{CACHE_KEY_PREFIX}:{wid}"
    except (TypeError, ValueError):
        return None
