"""
Step 207: Retry policy – exponential backoff, max attempts, skip after limit.
Crash-safe; never raises out of run_with_retry when skip_after_limit=True.
"""
import time
from typing import Any, Callable, Dict, Optional, TypeVar

from amazon_research.logging_config import get_logger

logger = get_logger("worker_stability.retry")

T = TypeVar("T")


def _retry_max() -> int:
    try:
        from amazon_research.worker_stability.policy import get_retry_max_attempts
        return get_retry_max_attempts()
    except Exception:
        return 3


def _backoff_seconds() -> int:
    try:
        from amazon_research.worker_stability.policy import get_retry_backoff_seconds
        return get_retry_backoff_seconds()
    except Exception:
        return 60


def run_with_retry(
    fn: Callable[[], T],
    workspace_id: Optional[int] = None,
    job_type: Optional[str] = None,
    max_attempts: Optional[int] = None,
    backoff_base_seconds: Optional[int] = None,
    skip_after_limit: bool = True,
) -> Dict[str, Any]:
    """
    Run fn() with retries. On exception: wait backoff (exponential), retry up to max_attempts.
    Returns {"ok": True, "result": <return value>} or {"ok": False, "error": str, "attempts": int}.
    If skip_after_limit and all retries failed, returns dict instead of raising.
    """
    max_a = max_attempts if max_attempts is not None else _retry_max()
    backoff = backoff_base_seconds if backoff_base_seconds is not None else _backoff_seconds()
    last_error: Optional[str] = None
    for attempt in range(1, max_a + 1):
        try:
            logger.info(
                "worker_stability worker job start workspace_id=%s job_type=%s attempt=%s",
                workspace_id, job_type, attempt,
                extra={"workspace_id": workspace_id, "job_type": job_type, "attempt": attempt},
            )
            result = fn()
            logger.info(
                "worker_stability worker job completion workspace_id=%s job_type=%s attempt=%s",
                workspace_id, job_type, attempt,
                extra={"workspace_id": workspace_id, "job_type": job_type, "attempt": attempt},
            )
            return {"ok": True, "result": result, "attempts": attempt}
        except Exception as e:
            last_error = str(e)
            logger.warning(
                "worker_stability worker job failure workspace_id=%s job_type=%s attempt=%s error=%s",
                workspace_id, job_type, attempt, last_error,
                extra={"workspace_id": workspace_id, "job_type": job_type, "attempt": attempt, "error": last_error},
            )
            if attempt < max_a:
                delay = backoff * (2 ** (attempt - 1))
                delay = min(delay, 3600)
                logger.info(
                    "worker_stability worker retry attempt workspace_id=%s job_type=%s next_attempt=%s delay_sec=%s",
                    workspace_id, job_type, attempt + 1, delay,
                    extra={"workspace_id": workspace_id, "job_type": job_type, "delay_seconds": delay},
                )
                time.sleep(delay)
            else:
                logger.warning(
                    "worker_stability worker retry limit reached workspace_id=%s job_type=%s attempts=%s",
                    workspace_id, job_type, max_a,
                    extra={"workspace_id": workspace_id, "job_type": job_type, "attempts": max_a},
                )
    if skip_after_limit:
        return {"ok": False, "error": last_error or "unknown", "attempts": max_a}
    raise RuntimeError(last_error)
