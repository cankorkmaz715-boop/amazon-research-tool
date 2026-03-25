"""
Step 221: Demo mode configuration. Reads DEMO_MODE_ENABLED from environment.
Demo mode is never persisted; it only affects in-memory response shaping.
"""
import os


def is_demo_mode_enabled() -> bool:
    """Return True if DEMO_MODE_ENABLED env is set to true (case-insensitive)."""
    return os.environ.get("DEMO_MODE_ENABLED", "").strip().lower() == "true"
