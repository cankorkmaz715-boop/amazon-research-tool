"""
Step 208: Resource guard policy – thresholds and behavior from env.
Safe defaults when env missing or invalid.
"""
import os
from typing import Any, Dict

from amazon_research.logging_config import get_logger

logger = get_logger("resource_guard.policy")

ENV_MEMORY_MB = "RESOURCE_GUARD_MEMORY_MB"
ENV_CPU_THRESHOLD = "RESOURCE_GUARD_CPU_THRESHOLD"
ENV_DEFER_ENABLED = "RESOURCE_GUARD_DEFER_ENABLED"
ENV_MAX_HEAVY_JOBS = "RESOURCE_GUARD_MAX_HEAVY_JOBS"
ENV_METRIC_FAILURE_ACTION = "RESOURCE_GUARD_METRIC_FAILURE_ACTION"

DEFAULT_MEMORY_MB = 2048
DEFAULT_CPU_THRESHOLD = 90.0
DEFAULT_MAX_HEAVY_JOBS = 10
METRIC_FAILURE_ALLOW = "allow"
METRIC_FAILURE_SKIP = "skip"


def _safe_float_env(key: str, default: float) -> float:
    try:
        v = os.environ.get(key)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return default
        return float(v.strip())
    except (ValueError, TypeError):
        return default


def _safe_int_env(key: str, default: int, min_val: int = 1) -> int:
    try:
        v = os.environ.get(key)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return default
        return max(min_val, int(v.strip()))
    except (ValueError, TypeError):
        return default


def get_memory_mb_threshold() -> int:
    """Memory pressure threshold in MB; above this we may defer/skip."""
    return _safe_int_env(ENV_MEMORY_MB, DEFAULT_MEMORY_MB)


def get_cpu_threshold() -> float:
    """CPU usage threshold (0–100); above this we may defer/skip if available."""
    return max(0.0, min(100.0, _safe_float_env(ENV_CPU_THRESHOLD, DEFAULT_CPU_THRESHOLD)))


def get_defer_enabled() -> bool:
    """If True, prefer defer over skip when over budget (caller may retry later)."""
    try:
        v = os.environ.get(ENV_DEFER_ENABLED)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return True
        return str(v).strip().lower() in ("1", "true", "yes")
    except Exception:
        return True


def get_max_heavy_jobs() -> int:
    """Max concurrent heavy jobs; above this we defer or skip."""
    return _safe_int_env(ENV_MAX_HEAVY_JOBS, DEFAULT_MAX_HEAVY_JOBS)


def get_metric_failure_action() -> str:
    """When metrics cannot be read: 'allow' or 'skip'. Default allow for resilience."""
    try:
        v = (os.environ.get(ENV_METRIC_FAILURE_ACTION) or "").strip().lower()
        if v in (METRIC_FAILURE_ALLOW, METRIC_FAILURE_SKIP):
            return v
        return METRIC_FAILURE_ALLOW
    except Exception:
        return METRIC_FAILURE_ALLOW


def get_policy_summary() -> Dict[str, Any]:
    """Current policy for logging/debug."""
    return {
        "memory_mb_threshold": get_memory_mb_threshold(),
        "cpu_threshold": get_cpu_threshold(),
        "defer_enabled": get_defer_enabled(),
        "max_heavy_jobs": get_max_heavy_jobs(),
        "metric_failure_action": get_metric_failure_action(),
    }
