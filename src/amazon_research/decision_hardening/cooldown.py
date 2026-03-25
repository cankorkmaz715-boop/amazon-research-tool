"""
Step 206: Refresh cooldown – suppress duplicate refresh for same workspace + path within protection window.
Thread-safe; in-memory. Never crashes callers.
"""
import time
import threading
from typing import Any, Dict, Optional, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("decision_hardening.cooldown")

_lock = threading.Lock()
# (workspace_id, path_key) -> last refresh timestamp (monotonic)
_last_refresh: Dict[Tuple[Any, str], float] = {}


def _cooldown_seconds() -> int:
    try:
        from amazon_research.decision_hardening.policy import get_cooldown_seconds
        return get_cooldown_seconds()
    except Exception:
        return 60


def check_refresh_cooldown(workspace_id: Optional[int], path_key: str) -> Tuple[bool, Optional[int]]:
    """
    Return (allowed, retry_after_seconds). If in cooldown, allowed=False and retry_after_seconds set.
    workspace_id must be valid; path_key must be non-empty. Invalid input -> (True, None) to avoid blocking.
    """
    if workspace_id is None or not (path_key or "").strip():
        return True, None
    path_key = (path_key or "").strip()
    now = time.monotonic()
    cooldown = _cooldown_seconds()
    key = (workspace_id, path_key)
    with _lock:
        last = _last_refresh.get(key)
        if last is None:
            return True, None
        elapsed = now - last
        if elapsed < cooldown:
            retry_after = max(1, int(cooldown - elapsed))
            logger.info(
                "decision_hardening duplicate refresh suppressed workspace_id=%s path_key=%s retry_after=%s",
                workspace_id, path_key, retry_after,
                extra={"workspace_id": workspace_id, "path_key": path_key, "retry_after_seconds": retry_after},
            )
            return False, retry_after
    return True, None


def record_refresh_done(workspace_id: Optional[int], path_key: str) -> None:
    """Call after a refresh for (workspace_id, path_key) completed successfully. Updates cooldown window."""
    if workspace_id is None or not (path_key or "").strip():
        return
    path_key = (path_key or "").strip()
    now = time.monotonic()
    key = (workspace_id, path_key)
    with _lock:
        _last_refresh[key] = now
    logger.debug("decision_hardening refresh recorded workspace_id=%s path_key=%s", workspace_id, path_key)


def get_cooldown_status_for_test(workspace_id: Optional[int], path_key: str) -> Optional[float]:
    """For tests only: last refresh time (monotonic) or None. Do not use in production logic."""
    if workspace_id is None or not (path_key or "").strip():
        return None
    key = (workspace_id, (path_key or "").strip())
    with _lock:
        return _last_refresh.get(key)
