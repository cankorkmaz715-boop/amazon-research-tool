"""
Step 204: Risk detection engine – workspace-scoped risk identification and classification.
"""
from .engine import (
    generate_workspace_risk_detection,
    RISK_HIGH,
    RISK_MEDIUM,
    RISK_LOW,
    RISK_COMPETITION,
    RISK_SATURATION,
    RISK_TREND_INSTABILITY,
    RISK_PORTFOLIO_CONCENTRATION,
    RISK_MARKET_ENTRY,
    RISK_ALERT_PATTERN,
    RISK_LOW_CONFIDENCE,
)

__all__ = [
    "generate_workspace_risk_detection",
    "RISK_HIGH",
    "RISK_MEDIUM",
    "RISK_LOW",
    "RISK_COMPETITION",
    "RISK_SATURATION",
    "RISK_TREND_INSTABILITY",
    "RISK_PORTFOLIO_CONCENTRATION",
    "RISK_MARKET_ENTRY",
    "RISK_ALERT_PATTERN",
    "RISK_LOW_CONFIDENCE",
]
