"""
Step 207: Job locking – lightweight in-memory lock per (workspace_id, job_type).
Prevents duplicate concurrent execution; stale locks auto-expire.
"""
import time
import threading
import uuid
from typing import Any, Dict, Optional, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("worker_stability.lock")

_lock = threading.Lock()
_held: Dict[Tuple[Any, str], Dict[str, Any]] = {}


def _stale_seconds() -> int:
    try:
        from amazon_research.worker_stability.policy import get_lock_stale_seconds
        return get_lock_stale_seconds()
    except Exception:
        return 900


def try_acquire(workspace_id: Optional[int], job_type: str) -> Tuple[bool, Optional[str]]:
    """
    Try to acquire lock for (workspace_id, job_type). Returns (acquired, lock_id).
    If lock exists and is not stale, returns (False, None). If stale or missing, acquire and return (True, lock_id).
    """
    job_type = (job_type or "").strip()
    if not job_type:
        return False, None
    key = (workspace_id, job_type)
    now = time.monotonic()
    stale_sec = _stale_seconds()
    with _lock:
        existing = _held.get(key)
        if existing:
            locked_at = existing.get("locked_at") or 0
            if now - locked_at < stale_sec:
                logger.debug(
                    "worker_stability lock not acquired (held) workspace_id=%s job_type=%s",
                    workspace_id, job_type,
                    extra={"workspace_id": workspace_id, "job_type": job_type},
                )
                return False, None
        lock_id = str(uuid.uuid4())[:8]
        _held[key] = {"locked_at": now, "lock_id": lock_id}
        logger.info(
            "worker_stability job lock acquire workspace_id=%s job_type=%s lock_id=%s",
            workspace_id, job_type, lock_id,
            extra={"workspace_id": workspace_id, "job_type": job_type, "lock_id": lock_id},
        )
        return True, lock_id


def release(workspace_id: Optional[int], job_type: str, lock_id: Optional[str] = None) -> bool:
    """Release lock for (workspace_id, job_type). If lock_id provided, only release if matching. Returns True if released."""
    job_type = (job_type or "").strip()
    if not job_type:
        return False
    key = (workspace_id, job_type)
    with _lock:
        existing = _held.get(key)
        if not existing:
            return False
        if lock_id is not None and existing.get("lock_id") != lock_id:
            return False
        del _held[key]
        logger.info(
            "worker_stability job lock release workspace_id=%s job_type=%s",
            workspace_id, job_type,
            extra={"workspace_id": workspace_id, "job_type": job_type},
        )
        return True


def release_force(workspace_id: Optional[int], job_type: str) -> bool:
    """Release lock regardless of lock_id (e.g. after timeout or crash recovery)."""
    job_type = (job_type or "").strip()
    if not job_type:
        return False
    key = (workspace_id, job_type)
    with _lock:
        if key in _held:
            del _held[key]
            logger.warning(
                "worker_stability job lock release_force workspace_id=%s job_type=%s",
                workspace_id, job_type,
                extra={"workspace_id": workspace_id, "job_type": job_type},
            )
            return True
    return False
