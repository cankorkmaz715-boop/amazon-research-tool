"""
Step 209: Error recovery policy – thresholds and behavior from env.
Safe defaults when env missing or invalid.
"""
import os
from typing import Any, Dict

from amazon_research.logging_config import get_logger

logger = get_logger("error_recovery.policy")

ENV_MAX_FAILURES = "ERROR_RECOVERY_MAX_FAILURES"
ENV_COOLDOWN_SECONDS = "ERROR_RECOVERY_COOLDOWN_SECONDS"
ENV_ENABLE_PARTIAL_FALLBACK = "ERROR_RECOVERY_ENABLE_PARTIAL_FALLBACK"
ENV_CIRCUIT_WINDOW_SECONDS = "ERROR_RECOVERY_CIRCUIT_WINDOW_SECONDS"

DEFAULT_MAX_FAILURES = 5
DEFAULT_COOLDOWN_SECONDS = 300
DEFAULT_CIRCUIT_WINDOW_SECONDS = 600


def _safe_int_env(key: str, default: int, min_val: int = 1) -> int:
    try:
        v = os.environ.get(key)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return default
        return max(min_val, int(v.strip()))
    except (ValueError, TypeError):
        return default


def get_max_failures() -> int:
    """Max failures in window before circuit suppresses re-execution."""
    return _safe_int_env(ENV_MAX_FAILURES, DEFAULT_MAX_FAILURES)


def get_cooldown_seconds() -> int:
    """Seconds to wait after threshold before allowing execution again."""
    return _safe_int_env(ENV_COOLDOWN_SECONDS, DEFAULT_COOLDOWN_SECONDS)


def get_enable_partial_fallback() -> bool:
    """Whether to use partial fallback when full cached/persisted unavailable."""
    try:
        v = os.environ.get(ENV_ENABLE_PARTIAL_FALLBACK)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return True
        return str(v).strip().lower() in ("1", "true", "yes")
    except Exception:
        return True


def get_circuit_window_seconds() -> int:
    """Time window in which failures are counted for circuit."""
    return _safe_int_env(ENV_CIRCUIT_WINDOW_SECONDS, DEFAULT_CIRCUIT_WINDOW_SECONDS)


def get_policy_summary() -> Dict[str, Any]:
    """Current policy for logging/debug."""
    return {
        "max_failures": get_max_failures(),
        "cooldown_seconds": get_cooldown_seconds(),
        "enable_partial_fallback": get_enable_partial_fallback(),
        "circuit_window_seconds": get_circuit_window_seconds(),
    }
