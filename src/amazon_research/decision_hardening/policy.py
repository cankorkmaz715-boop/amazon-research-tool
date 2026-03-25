"""
Step 206: Decision path policy – cooldowns and rate limits from env.
Safe defaults when env missing or invalid.
"""
import os
from typing import Any, Dict

from amazon_research.logging_config import get_logger

logger = get_logger("decision_hardening.policy")

# Env keys
ENV_COOLDOWN = "DECISION_REFRESH_COOLDOWN_SECONDS"
ENV_REFRESH_MAX = "DECISION_REFRESH_MAX_PER_MINUTE"
ENV_READ_MAX = "DECISION_READ_MAX_PER_MINUTE"

# Safe defaults
DEFAULT_COOLDOWN_SECONDS = 60
DEFAULT_REFRESH_MAX_PER_MINUTE = 10
DEFAULT_READ_MAX_PER_MINUTE = 60


def _safe_int_env(key: str, default: int) -> int:
    try:
        v = os.environ.get(key)
        if v is None or v.strip() == "":
            return default
        return max(1, int(v.strip()))
    except (ValueError, TypeError):
        return default


def get_cooldown_seconds() -> int:
    """Protection window: no duplicate refresh for same workspace+path within this many seconds."""
    v = _safe_int_env(ENV_COOLDOWN, DEFAULT_COOLDOWN_SECONDS)
    if v != DEFAULT_COOLDOWN_SECONDS:
        logger.debug("decision_hardening policy cooldown_seconds=%s from env", v)
    return v


def get_refresh_max_per_minute() -> int:
    """Max decision-refresh requests per workspace per minute (rate limit)."""
    return _safe_int_env(ENV_REFRESH_MAX, DEFAULT_REFRESH_MAX_PER_MINUTE)


def get_read_max_per_minute() -> int:
    """Max decision-read requests per workspace per minute (rate limit)."""
    return _safe_int_env(ENV_READ_MAX, DEFAULT_READ_MAX_PER_MINUTE)


def get_policy_summary() -> Dict[str, Any]:
    """Return current policy for logging/debug; never used for enforcement."""
    return {
        "cooldown_seconds": get_cooldown_seconds(),
        "refresh_max_per_minute": get_refresh_max_per_minute(),
        "read_max_per_minute": get_read_max_per_minute(),
    }
