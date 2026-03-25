"""
Step 208: Execution budget – track concurrent heavy jobs, enforce max.
Prevents too many heavy jobs running at once; integrates with guard decision.
"""
import threading
from typing import Any, Dict, Set, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("resource_guard.budget")

_lock = threading.Lock()
_heavy_active: Set[Tuple[Any, str]] = set()

HEAVY_JOB_TYPES = frozenset({
    "intelligence_refresh",
    "strategy",
    "strategy_opportunities",
    "portfolio_recommendation",
    "market_entry_signals",
    "risk_detection",
    "strategic_scoring",
    "discovery",
    "refresh",
    "scoring",
})


def _max_heavy() -> int:
    try:
        from amazon_research.resource_guard.policy import get_max_heavy_jobs
        return get_max_heavy_jobs()
    except Exception:
        return 10


def is_heavy_job_type(job_type: str) -> bool:
    """True if job_type is considered heavy for budget."""
    return (job_type or "").strip() in HEAVY_JOB_TYPES


def get_heavy_job_count() -> int:
    """Current number of running heavy jobs."""
    with _lock:
        return len(_heavy_active)


def would_exceed_heavy_budget() -> bool:
    """True if one more heavy job would exceed max (used before starting)."""
    with _lock:
        return len(_heavy_active) >= _max_heavy()


def record_heavy_job_start(workspace_id: Any, job_type: str) -> None:
    """Record start of a heavy job. Call before running."""
    job_type = (job_type or "").strip()
    if not job_type or job_type not in HEAVY_JOB_TYPES:
        return
    key = (workspace_id, job_type)
    with _lock:
        _heavy_active.add(key)
    logger.debug(
        "resource_guard heavy job start workspace_id=%s job_type=%s count=%s",
        workspace_id, job_type, len(_heavy_active),
        extra={"workspace_id": workspace_id, "job_type": job_type},
    )


def record_heavy_job_end(workspace_id: Any, job_type: str) -> None:
    """Record end of a heavy job. Call in finally after running."""
    job_type = (job_type or "").strip()
    if not job_type or job_type not in HEAVY_JOB_TYPES:
        return
    key = (workspace_id, job_type)
    with _lock:
        _heavy_active.discard(key)
    logger.debug(
        "resource_guard heavy job end workspace_id=%s job_type=%s",
        workspace_id, job_type,
        extra={"workspace_id": workspace_id, "job_type": job_type},
    )


def get_budget_summary() -> Dict[str, Any]:
    """Summary for health/logging."""
    with _lock:
        count = len(_heavy_active)
        max_heavy = _max_heavy()
    return {
        "heavy_job_count": count,
        "max_heavy_jobs": max_heavy,
        "budget_exceeded": count >= max_heavy,
    }
