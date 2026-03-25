"""
Step 194: Workspace intelligence cache layer – in-memory TTL cache for workspace summaries.
Prefer cache hit; on miss fall back to persistence then compute; warm cache after persistence or compute.
Never crashes; logs hit/miss/write/invalidation/fallback.
"""
import time
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

from .cache_keys import workspace_intelligence_cache_key
from .cache_policy import get_cache_ttl_seconds

logger = get_logger("workspace_intelligence.cache")

# In-memory store: key -> (payload dict, expires_at timestamp). Process-local.
_cache: Dict[str, tuple] = {}


def get_cached_summary(workspace_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """
    Read cached workspace intelligence summary. Returns None on miss, expired, or error.
    Logs cache read hit or miss with workspace_id.
    """
    key = workspace_intelligence_cache_key(workspace_id)
    if not key:
        return None
    try:
        try:
            from amazon_research.workspace_isolation import require_workspace_context
            if require_workspace_context(workspace_id, "cache_read"):
                logger.debug("workspace_intelligence cache workspace scope enforcement workspace_id=%s", workspace_id, extra={"workspace_id": workspace_id})
        except Exception:
            pass
        entry = _cache.get(key)
        if entry is None:
            logger.info(
                "workspace_intelligence cache read miss workspace_id=%s",
                workspace_id,
                extra={"workspace_id": workspace_id, "cache_key": key},
            )
            return None
        payload, expires_at = entry
        if not isinstance(expires_at, (int, float)) or time.time() > expires_at:
            _cache.pop(key, None)
            logger.info(
                "workspace_intelligence cache read miss workspace_id=%s reason=expired",
                workspace_id,
                extra={"workspace_id": workspace_id, "cache_key": key},
            )
            return None
        if not isinstance(payload, dict):
            _cache.pop(key, None)
            return None
        logger.info(
            "workspace_intelligence cache read hit workspace_id=%s",
            workspace_id,
            extra={"workspace_id": workspace_id, "cache_key": key},
        )
        return dict(payload)
    except Exception as e:
        logger.warning(
            "workspace_intelligence cache read failure workspace_id=%s: %s",
            workspace_id,
            e,
            extra={"workspace_id": workspace_id},
        )
        return None


def set_cached_summary(
    workspace_id: Optional[int],
    summary: Dict[str, Any],
    ttl_seconds: Optional[int] = None,
) -> None:
    """
    Write workspace intelligence summary to cache. No-op on invalid input or error.
    Logs cache write success or failure.
    """
    key = workspace_intelligence_cache_key(workspace_id)
    if not key:
        return
    if not isinstance(summary, dict):
        return
    try:
        try:
            from amazon_research.workspace_isolation import require_workspace_context
            if require_workspace_context(workspace_id, "cache_write"):
                logger.debug("workspace_intelligence cache workspace scope enforcement workspace_id=%s", workspace_id, extra={"workspace_id": workspace_id})
        except Exception:
            pass
        ttl = ttl_seconds if ttl_seconds is not None else get_cache_ttl_seconds()
        expires_at = time.time() + max(1, ttl)
        _cache[key] = (dict(summary), expires_at)
        logger.info(
            "workspace_intelligence cache write success workspace_id=%s ttl_seconds=%s",
            workspace_id,
            ttl,
            extra={"workspace_id": workspace_id, "cache_key": key, "ttl_seconds": ttl},
        )
    except Exception as e:
        logger.warning(
            "workspace_intelligence cache write failure workspace_id=%s: %s",
            workspace_id,
            e,
            extra={"workspace_id": workspace_id},
        )


def invalidate_cached_summary(workspace_id: Optional[int]) -> None:
    """
    Remove workspace intelligence summary from cache (invalidation / refresh).
    Logs cache invalidation. No-op on error.
    """
    key = workspace_intelligence_cache_key(workspace_id)
    if not key:
        return
    try:
        if key in _cache:
            del _cache[key]
            logger.info(
                "workspace_intelligence cache invalidation workspace_id=%s",
                workspace_id,
                extra={"workspace_id": workspace_id, "cache_key": key},
            )
    except Exception as e:
        logger.warning(
            "workspace_intelligence cache invalidation failure workspace_id=%s: %s",
            workspace_id,
            e,
            extra={"workspace_id": workspace_id},
        )
