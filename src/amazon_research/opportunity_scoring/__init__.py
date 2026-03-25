"""
Step 235: Real opportunity scoring & ranking calibration.
Reuses existing ranking data; deterministic priority bands and sort order.
"""
from amazon_research.opportunity_scoring.opportunity_scoring_service import get_calibrated_opportunity_rows
from amazon_research.opportunity_scoring.opportunity_ranking_calibrator import calibrate_opportunity_rows
from amazon_research.opportunity_scoring.opportunity_score_mapper import (
    score_to_normalized,
    score_to_priority_band,
    build_supporting_signal_hints,
)
from amazon_research.opportunity_scoring.opportunity_score_types import (
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    DEFAULT_HIGH_THRESHOLD,
    DEFAULT_MEDIUM_THRESHOLD,
)

__all__ = [
    "get_calibrated_opportunity_rows",
    "calibrate_opportunity_rows",
    "score_to_normalized",
    "score_to_priority_band",
    "build_supporting_signal_hints",
    "PRIORITY_HIGH",
    "PRIORITY_MEDIUM",
    "PRIORITY_LOW",
    "DEFAULT_HIGH_THRESHOLD",
    "DEFAULT_MEDIUM_THRESHOLD",
]
