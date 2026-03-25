"""
Step 207: Worker health monitoring – active jobs, stalled detection, excessive retries.
Lightweight in-process; for debugging and observability.
"""
import time
import threading
from typing import Any, Dict, List, Set, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("worker_stability.health")

_lock = threading.Lock()
_active: Set[Tuple[Any, str]] = set()
_active_start: Dict[Tuple[Any, str], float] = {}
_retry_counts: Dict[Tuple[Any, str], int] = {}
_max_active_for_starvation: int = 0


def _max_active() -> int:
    try:
        from amazon_research.worker_stability.policy import get_max_active_jobs
        return get_max_active_jobs()
    except Exception:
        return 50


def record_start(workspace_id: Any, job_type: str) -> None:
    """Record job start for health tracking."""
    key = (workspace_id, (job_type or "").strip())
    if not key[1]:
        return
    with _lock:
        _active.add(key)
        _active_start[key] = time.monotonic()
    global _max_active_for_starvation
    with _lock:
        _max_active_for_starvation = max(_max_active_for_starvation, len(_active))


def record_end(workspace_id: Any, job_type: str) -> None:
    """Record job end."""
    key = (workspace_id, (job_type or "").strip())
    if not key[1]:
        return
    with _lock:
        _active.discard(key)
        _active_start.pop(key, None)


def record_retry(workspace_id: Any, job_type: str) -> None:
    """Record a retry attempt for (workspace_id, job_type)."""
    key = (workspace_id, (job_type or "").strip())
    if not key[1]:
        return
    with _lock:
        _retry_counts[key] = _retry_counts.get(key, 0) + 1


def get_active_count() -> int:
    """Current number of active (running) jobs."""
    with _lock:
        return len(_active)


def get_stalled(threshold_seconds: float) -> List[Dict[str, Any]]:
    """Jobs that have been active longer than threshold_seconds."""
    now = time.monotonic()
    with _lock:
        out = []
        for key in list(_active):
            t0 = _active_start.get(key)
            if t0 is not None and now - t0 > threshold_seconds:
                out.append({
                    "workspace_id": key[0],
                    "job_type": key[1],
                    "duration_seconds": round(now - t0, 1),
                })
        return out


def get_excessive_retries(threshold: int = 5) -> List[Dict[str, Any]]:
    """Entries with retry count >= threshold."""
    with _lock:
        return [
            {"workspace_id": k[0], "job_type": k[1], "retry_count": v}
            for k, v in _retry_counts.items()
            if v >= threshold
        ]


def get_health_summary() -> Dict[str, Any]:
    """Health indicators for debugging. Avoids holding lock across get_stalled/get_excessive_retries to prevent deadlock."""
    active_count = get_active_count()
    stalled = get_stalled(300.0)
    excessive = get_excessive_retries(5)
    with _lock:
        max_seen = _max_active_for_starvation
    return {
        "active_job_count": active_count,
        "max_active_seen": max_seen,
        "stalled_count": len(stalled),
        "stalled_sample": stalled[:5],
        "excessive_retry_count": len(excessive),
        "excessive_retry_sample": excessive[:5],
    }


def would_starve() -> bool:
    """True if accepting another job would exceed max active (queue starvation protection)."""
    with _lock:
        return len(_active) >= _max_active()
