"""
Step 209: Circuit / failsafe – track failures per (workspace_id, path_key), suppress when threshold exceeded.
Allows recovery after cooldown. In-memory; no persistence.
"""
import time
import threading
from typing import Any, Dict, List, Optional, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("error_recovery.circuit")

_lock = threading.Lock()
_failures: Dict[Tuple[Any, str], List[float]] = {}
_last_failure: Dict[Tuple[Any, str], float] = {}


def _max_failures() -> int:
    try:
        from amazon_research.error_recovery.policy import get_max_failures
        return get_max_failures()
    except Exception:
        return 5


def _cooldown_seconds() -> int:
    try:
        from amazon_research.error_recovery.policy import get_cooldown_seconds
        return get_cooldown_seconds()
    except Exception:
        return 300


def _window_seconds() -> int:
    try:
        from amazon_research.error_recovery.policy import get_circuit_window_seconds
        return get_circuit_window_seconds()
    except Exception:
        return 600


def _prune(timestamps: List[float]) -> List[float]:
    """Keep only timestamps within circuit window."""
    now = time.monotonic()
    window = _window_seconds()
    return [t for t in timestamps if now - t < window]


def record_failure(workspace_id: Any, path_key: str) -> None:
    """Record a failure for (workspace_id, path_key)."""
    path_key = (path_key or "").strip()
    if not path_key:
        return
    key = (workspace_id, path_key)
    now = time.monotonic()
    with _lock:
        _failures.setdefault(key, []).append(now)
        _failures[key] = _prune(_failures[key])
        _last_failure[key] = now
    count = len(_failures[key])
    if count >= _max_failures():
        logger.warning(
            "error_recovery repeated failure threshold reached workspace_id=%s path_key=%s failures=%s",
            workspace_id, path_key, count,
            extra={"workspace_id": workspace_id, "path_key": path_key, "failure_count": count},
        )
        logger.warning(
            "error_recovery circuit/failsafe suppression activated workspace_id=%s path_key=%s",
            workspace_id, path_key,
            extra={"workspace_id": workspace_id, "path_key": path_key},
        )


def record_success(workspace_id: Any, path_key: str) -> None:
    """Record success; clears failure count for this key (fresh start)."""
    path_key = (path_key or "").strip()
    if not path_key:
        return
    key = (workspace_id, path_key)
    with _lock:
        _failures.pop(key, None)
        _last_failure.pop(key, None)


def is_suppressed(workspace_id: Any, path_key: str) -> Tuple[bool, Optional[int]]:
    """
    True if execution should be suppressed (too many failures in window, still in cooldown).
    Returns (suppressed, retry_after_seconds). retry_after_seconds is set when suppressed.
    """
    path_key = (path_key or "").strip()
    if not path_key:
        return False, None
    key = (workspace_id, path_key)
    now = time.monotonic()
    with _lock:
        timestamps = _prune(_failures.get(key, [])[:])
        last = _last_failure.get(key)
    if len(timestamps) < _max_failures():
        return False, None
    cooldown = _cooldown_seconds()
    if last is None:
        return True, cooldown
    elapsed = now - last
    if elapsed >= cooldown:
        logger.info(
            "error_recovery cooldown expired workspace_id=%s path_key=%s",
            workspace_id, path_key,
            extra={"workspace_id": workspace_id, "path_key": path_key},
        )
        with _lock:
            _failures.pop(key, None)
            _last_failure.pop(key, None)
        return False, None
    return True, max(1, int(cooldown - elapsed))


def get_circuit_summary(workspace_id: Optional[Any] = None, path_key: Optional[str] = None) -> Dict[str, Any]:
    """Summary for logging; optionally filter by workspace_id/path_key."""
    with _lock:
        if workspace_id is not None and path_key is not None:
            key = (workspace_id, (path_key or "").strip())
            count = len(_prune(_failures.get(key, [])))
            return {"failure_count": count, "suppressed": count >= _max_failures()}
        total_keys = len(_failures)
        total_failures = sum(len(_prune(ts)) for ts in _failures.values())
        return {"keys_tracked": total_keys, "total_failures_in_window": total_failures}
