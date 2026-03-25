"""
Step 225: Feature flags – resolve full set for API/consumers.
"""
from typing import Any, Dict

from amazon_research.feature_flags.config import DEFAULT_FLAGS, get_flag_from_env


def get_feature_flags() -> Dict[str, Any]:
    """
    Return current feature flags as a flat dict of name -> bool.
    Safe: never raises; always returns all known flags with env-based or default values.
    """
    out: Dict[str, Any] = {}
    for name in DEFAULT_FLAGS:
        try:
            out[name] = get_flag_from_env(name)
        except Exception:
            out[name] = DEFAULT_FLAGS.get(name, True)
    return out


def is_feature_enabled(flag_name: str) -> bool:
    """Return True if the given flag is enabled. Safe: unknown flag returns True (no break)."""
    try:
        return bool(get_flag_from_env(flag_name))
    except Exception:
        return True
