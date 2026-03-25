"""
Step 235: Real opportunity scoring & ranking calibration – types and priority bands.
Deterministic, explainable; tunable via constants.
"""
from typing import Any, Dict, List, Optional

# Priority bands for dashboard/API (stable)
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# Score normalization range (dashboard-facing)
NORMALIZED_SCORE_MIN = 0.0
NORMALIZED_SCORE_MAX = 100.0

# Calibration thresholds (tunable; used for priority band and fallback)
DEFAULT_HIGH_THRESHOLD = 70.0
DEFAULT_MEDIUM_THRESHOLD = 50.0


def priority_band_from_score(score: Optional[float], high: float = DEFAULT_HIGH_THRESHOLD, medium: float = DEFAULT_MEDIUM_THRESHOLD) -> str:
    """Map raw score to priority band. Deterministic."""
    if score is None:
        return PRIORITY_LOW
    try:
        s = float(score)
        if s >= high:
            return PRIORITY_HIGH
        if s >= medium:
            return PRIORITY_MEDIUM
    except (TypeError, ValueError):
        pass
    return PRIORITY_LOW


def normalized_score(raw: Optional[float], min_val: float = NORMALIZED_SCORE_MIN, max_val: float = NORMALIZED_SCORE_MAX) -> float:
    """Clamp score to normalized range. No rescaling; just clamp for stability."""
    if raw is None:
        return min_val
    try:
        s = float(raw)
        if s < min_val:
            return min_val
        if s > max_val:
            return max_val
        return round(s, 2)
    except (TypeError, ValueError):
        return min_val
