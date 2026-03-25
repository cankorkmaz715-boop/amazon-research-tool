"""
Step 225: Feature flags – env-based config. Safe defaults; no secrets.
"""
import os
from typing import Dict, Optional

# All known flags; safe default = True for backward compatibility (no behavior change when unset)
DEFAULT_FLAGS: Dict[str, bool] = {
    "demo_mode": True,
    "walkthrough_enabled": True,
    "onboarding_enabled": True,
    "usage_analytics_enabled": True,
    "alert_center_enabled": True,
    "copilot_context_enabled": True,
}

# Env var name per flag (optional override; if unset, use DEFAULT_FLAGS)
ENV_MAP: Dict[str, str] = {
    "demo_mode": "FEATURE_DEMO_MODE",
    "walkthrough_enabled": "FEATURE_WALKTHROUGH",
    "onboarding_enabled": "FEATURE_ONBOARDING",
    "usage_analytics_enabled": "FEATURE_ANALYTICS",
    "alert_center_enabled": "FEATURE_ALERT_CENTER",
    "copilot_context_enabled": "FEATURE_COPILOT_CONTEXT",
}

# Legacy: demo also respects DEMO_MODE_ENABLED when FEATURE_DEMO_MODE not set
DEMO_MODE_ENABLED_ENV = "DEMO_MODE_ENABLED"


def _parse_bool(value: str) -> Optional[bool]:
    """Parse env string to bool; empty or unknown => None (use default)."""
    if value is None:
        return None
    v = (value or "").strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    return None


def get_flag_from_env(flag_name: str) -> bool:
    """
    Resolve a single flag: env override or safe default.
    Never raises; missing flag name returns default True for known flags.
    """
    default = DEFAULT_FLAGS.get(flag_name, True)
    env_key = ENV_MAP.get(flag_name)
    if not env_key:
        return default
    raw = os.environ.get(env_key, "").strip()
    if not raw and flag_name == "demo_mode":
        # Legacy: check DEMO_MODE_ENABLED for demo_mode
        raw = os.environ.get(DEMO_MODE_ENABLED_ENV, "").strip()
    parsed = _parse_bool(raw)
    return parsed if parsed is not None else default
