"""
Step 201: Opportunity strategy engine – structured strategic guidance from workspace opportunity data.
"""
from .engine import (
    generate_workspace_opportunity_strategy,
    STRATEGY_ACT_NOW,
    STRATEGY_MONITOR,
    STRATEGY_DEPRIORITIZE,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
)

__all__ = [
    "generate_workspace_opportunity_strategy",
    "STRATEGY_ACT_NOW",
    "STRATEGY_MONITOR",
    "STRATEGY_DEPRIORITIZE",
    "PRIORITY_HIGH",
    "PRIORITY_MEDIUM",
    "PRIORITY_LOW",
]
