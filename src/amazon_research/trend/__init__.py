"""
Trend engine. Step 80 – rule-based trend signals; Step 87 – trend scoring v2.
"""
from .engine import (
    TREND_FALLING,
    TREND_INSUFFICIENT,
    TREND_NOISY,
    TREND_RISING,
    TREND_STABLE,
    get_price_trend,
    get_rank_trend,
    get_rating_trend,
    get_review_count_trend,
    get_trends_for_asin,
)
from .scoring import score_trends

__all__ = [
    "TREND_RISING",
    "TREND_FALLING",
    "TREND_STABLE",
    "TREND_NOISY",
    "TREND_INSUFFICIENT",
    "get_price_trend",
    "get_review_count_trend",
    "get_rating_trend",
    "get_rank_trend",
    "get_trends_for_asin",
    "score_trends",
]
