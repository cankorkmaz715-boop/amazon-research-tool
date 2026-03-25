"""
Rate limiting v1. Step 57 – in-memory sliding window per (workspace_id, bucket).
Lightweight, internal-first. Protects API and export; clear result when exceeded.
Step 206: decision_read and decision_refresh buckets for decision path hardening.
"""
import os
import time
import threading
from collections import deque
from typing import Any, Dict, Optional, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("rate_limit")

_lock = threading.Lock()
# key: (workspace_id, bucket) -> deque of timestamps (float)
_buckets: Dict[Tuple[Any, str], deque] = {}

# Default window in seconds
DEFAULT_WINDOW_SEC = 60


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded. Step 57."""
    def __init__(self, bucket: str, retry_after_seconds: int, message: Optional[str] = None):
        self.bucket = bucket
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message or f"rate limit exceeded: {bucket}, retry after {retry_after_seconds}s")


def _key(workspace_id: Optional[int], bucket: str) -> Tuple[Any, str]:
    return (workspace_id, bucket)


def _prune(deq: deque, now: float, window_sec: float) -> None:
    cutoff = now - window_sec
    while deq and deq[0] < cutoff:
        deq.popleft()


def check_rate_limit(
    workspace_id: Optional[int],
    bucket: str,
    limit: int,
    window_sec: float = DEFAULT_WINDOW_SEC,
) -> Tuple[bool, Optional[int]]:
    """
    Check if the request is within rate limit. Returns (allowed, retry_after_seconds).
    retry_after_seconds is set only when allowed=False (suggested wait before retry).
    """
    if limit <= 0:
        return True, None
    now = time.monotonic()
    key = _key(workspace_id, bucket)
    with _lock:
        if key not in _buckets:
            _buckets[key] = deque()
        deq = _buckets[key]
        _prune(deq, now, window_sec)
        if len(deq) >= limit:
            # Oldest timestamp in window: deq[0]. Retry after (deq[0] + window_sec - now) seconds
            retry_after = max(1, int(deq[0] + window_sec - now))
            return False, retry_after
    return True, None


def record_rate_limit(workspace_id: Optional[int], bucket: str) -> None:
    """Record one request for the (workspace_id, bucket). Call after allowing the request."""
    now = time.monotonic()
    key = _key(workspace_id, bucket)
    with _lock:
        if key not in _buckets:
            _buckets[key] = deque()
        _buckets[key].append(now)


def _decision_limit_from_env(bucket: str) -> int:
    """Step 206: Limits for decision_read / decision_refresh from env."""
    if bucket == "decision_read":
        v = os.environ.get("DECISION_READ_MAX_PER_MINUTE", "60")
    elif bucket == "decision_refresh":
        v = os.environ.get("DECISION_REFRESH_MAX_PER_MINUTE", "10")
    else:
        return 60
    try:
        return max(1, int(v.strip()))
    except (ValueError, TypeError):
        return 60 if bucket == "decision_read" else 10


def get_effective_rate_limit(workspace_id: Optional[int], bucket: str) -> int:
    """
    Step 60: Return rate limit from workspace's plan.billing_metadata if set, else from config.
    bucket "api" -> rate_limit_api_per_minute, "export" -> rate_limit_export_per_minute.
    Step 206: "decision_read" and "decision_refresh" use DECISION_READ_MAX_PER_MINUTE / DECISION_REFRESH_MAX_PER_MINUTE.
    """
    if bucket in ("decision_read", "decision_refresh"):
        return _decision_limit_from_env(bucket)
    if workspace_id is None:
        from amazon_research.config import get_config
        cfg = get_config()
        return cfg.rate_limit_api_per_minute if bucket == "api" else cfg.rate_limit_export_per_minute
    try:
        from amazon_research.db import get_workspace_plan
        from amazon_research.config import get_config
        plan = get_workspace_plan(workspace_id)
        cfg = get_config()
        default = cfg.rate_limit_api_per_minute if bucket == "api" else cfg.rate_limit_export_per_minute
        if plan and plan.get("active") and plan.get("billing_metadata") and isinstance(plan["billing_metadata"], dict):
            key = "rate_limit_api_per_minute" if bucket == "api" else "rate_limit_export_per_minute"
            val = plan["billing_metadata"].get(key)
            if val is not None and isinstance(val, (int, float)) and int(val) > 0:
                return int(val)
        return default
    except Exception:
        from amazon_research.config import get_config
        cfg = get_config()
        return cfg.rate_limit_api_per_minute if bucket == "api" else cfg.rate_limit_export_per_minute


def check_and_raise(
    workspace_id: Optional[int],
    bucket: str,
    limit: int,
    window_sec: float = DEFAULT_WINDOW_SEC,
) -> None:
    """If over limit, raise RateLimitExceededError. Otherwise no-op. Call record_rate_limit after success."""
    allowed, retry_after = check_rate_limit(workspace_id, bucket, limit, window_sec)
    if not allowed and retry_after is not None:
        raise RateLimitExceededError(bucket, retry_after)
