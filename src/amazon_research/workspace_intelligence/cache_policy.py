"""
Step 194: Workspace intelligence cache policy – TTL and behavior from env.
"""
import os
from typing import Optional

ENV_CACHE_TTL_SECONDS = "WORKSPACE_INTELLIGENCE_CACHE_TTL_SECONDS"
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes


def get_cache_ttl_seconds() -> int:
    """Cache TTL in seconds. From env or default. Never returns < 1."""
    try:
        v = os.environ.get(ENV_CACHE_TTL_SECONDS, "").strip()
        if v:
            return max(1, int(v))
    except (ValueError, TypeError):
        pass
    return DEFAULT_CACHE_TTL_SECONDS
