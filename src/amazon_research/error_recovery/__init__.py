"""
Step 209: Error recovery and failsafe execution – circuit, fallback order, stable failure shape.
"""
from .policy import (
    get_max_failures,
    get_cooldown_seconds,
    get_enable_partial_fallback,
    get_circuit_window_seconds,
    get_policy_summary,
)
from .circuit import (
    record_failure,
    record_success,
    is_suppressed,
    get_circuit_summary,
)
from .failsafe import (
    run_with_failsafe,
    stable_failure_response,
)

__all__ = [
    "get_max_failures",
    "get_cooldown_seconds",
    "get_enable_partial_fallback",
    "get_circuit_window_seconds",
    "get_policy_summary",
    "record_failure",
    "record_success",
    "is_suppressed",
    "get_circuit_summary",
    "run_with_failsafe",
    "stable_failure_response",
]
