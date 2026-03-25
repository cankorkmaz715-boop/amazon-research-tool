"""
Opportunity alert engine. Step 107 – detect important opportunity changes from research signals.
"""
from .opportunity_alert_engine import (
    evaluate_opportunity_alerts,
    ALERT_NEW_STRONG_CANDIDATE,
    ALERT_OPPORTUNITY_INCREASE,
    ALERT_TREND_SCORE_CHANGE,
    ALERT_COMPETITION_DROP,
    ALERT_DEMAND_INCREASE,
    TARGET_TYPE_CLUSTER,
    TARGET_TYPE_NICHE,
    TARGET_TYPE_ASIN,
)

__all__ = [
    "evaluate_opportunity_alerts",
    "ALERT_NEW_STRONG_CANDIDATE",
    "ALERT_OPPORTUNITY_INCREASE",
    "ALERT_TREND_SCORE_CHANGE",
    "ALERT_COMPETITION_DROP",
    "ALERT_DEMAND_INCREASE",
    "TARGET_TYPE_CLUSTER",
    "TARGET_TYPE_NICHE",
    "TARGET_TYPE_ASIN",
]
