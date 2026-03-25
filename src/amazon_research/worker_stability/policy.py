"""
Step 207: Worker stability policy – retry and timeout from env.
Safe defaults when env missing or invalid.
"""
import os
from typing import Any, Dict

from amazon_research.logging_config import get_logger

logger = get_logger("worker_stability.policy")

ENV_RETRY_MAX = "WORKER_RETRY_MAX_ATTEMPTS"
ENV_BACKOFF = "WORKER_RETRY_BACKOFF_SECONDS"
ENV_JOB_TIMEOUT = "WORKER_JOB_TIMEOUT_SECONDS"
ENV_MAX_ACTIVE = "WORKER_MAX_ACTIVE_JOBS"
ENV_LOCK_STALE_SECONDS = "WORKER_LOCK_STALE_SECONDS"

DEFAULT_RETRY_MAX = 3
DEFAULT_BACKOFF_SECONDS = 60
DEFAULT_JOB_TIMEOUT_SECONDS = 600
DEFAULT_MAX_ACTIVE_JOBS = 50
DEFAULT_LOCK_STALE_SECONDS = 900


def _safe_int_env(key: str, default: int, min_val: int = 1) -> int:
    try:
        v = os.environ.get(key)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return default
        return max(min_val, int(v.strip()))
    except (ValueError, TypeError):
        return default


def get_retry_max_attempts() -> int:
    """Max retry attempts before skipping job as permanently failing."""
    return _safe_int_env(ENV_RETRY_MAX, DEFAULT_RETRY_MAX)


def get_retry_backoff_seconds() -> int:
    """Base delay in seconds for retry backoff (exponential: backoff * 2^attempt)."""
    return _safe_int_env(ENV_BACKOFF, DEFAULT_BACKOFF_SECONDS)


def get_job_timeout_seconds() -> int:
    """Max seconds a single job run may take before timeout."""
    return _safe_int_env(ENV_JOB_TIMEOUT, DEFAULT_JOB_TIMEOUT_SECONDS)


def get_max_active_jobs() -> int:
    """Max concurrent active jobs for queue starvation protection."""
    return _safe_int_env(ENV_MAX_ACTIVE, DEFAULT_MAX_ACTIVE_JOBS)


def get_lock_stale_seconds() -> int:
    """Locks older than this are considered stale and can be overridden."""
    return _safe_int_env(ENV_LOCK_STALE_SECONDS, DEFAULT_LOCK_STALE_SECONDS)


def get_policy_summary() -> Dict[str, Any]:
    """Current policy for logging/debug."""
    return {
        "retry_max_attempts": get_retry_max_attempts(),
        "retry_backoff_seconds": get_retry_backoff_seconds(),
        "job_timeout_seconds": get_job_timeout_seconds(),
        "max_active_jobs": get_max_active_jobs(),
        "lock_stale_seconds": get_lock_stale_seconds(),
    }
