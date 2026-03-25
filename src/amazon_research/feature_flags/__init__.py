"""
Step 225: Feature flags & safe rollout. Env-based; no external vendor.
"""
from amazon_research.feature_flags.config import DEFAULT_FLAGS, ENV_MAP, get_flag_from_env
from amazon_research.feature_flags.resolver import get_feature_flags, is_feature_enabled

__all__ = [
    "get_feature_flags",
    "is_feature_enabled",
    "get_flag_from_env",
    "DEFAULT_FLAGS",
    "ENV_MAP",
]
