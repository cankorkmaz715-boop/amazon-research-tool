"""
Step 207: Timeout protection – run callable with max duration.
Uses concurrent.futures for cross-platform timeout; crash-safe.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable, TypeVar

from amazon_research.logging_config import get_logger

logger = get_logger("worker_stability.timeout")

T = TypeVar("T")


def _default_timeout_seconds() -> int:
    try:
        from amazon_research.worker_stability.policy import get_job_timeout_seconds
        return get_job_timeout_seconds()
    except Exception:
        return 600


def run_with_timeout(
    fn: Callable[[], T],
    timeout_seconds: int,
    workspace_id: Any = None,
    job_type: Any = None,
) -> T:
    """Run fn() in a thread with timeout. Raises TimeoutError if exceeded. Caller should catch."""
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=max(1, timeout_seconds))
        except FuturesTimeoutError:
            logger.warning(
                "worker_stability job timeout workspace_id=%s job_type=%s timeout_sec=%s",
                workspace_id, job_type, timeout_seconds,
                extra={"workspace_id": workspace_id, "job_type": job_type, "timeout_seconds": timeout_seconds},
            )
            raise TimeoutError(f"job timed out after {timeout_seconds}s")
