"""
Step 235: Map raw ranking data to normalized score and supporting signal hints.
Reuses opportunity_rankings fields only; no extra engine calls.
"""
from typing import Any, Dict, List, Optional

from amazon_research.opportunity_scoring.opportunity_score_types import (
    NORMALIZED_SCORE_MAX,
    NORMALIZED_SCORE_MIN,
    normalized_score as clamp_normalized,
    priority_band_from_score,
)


def score_to_normalized(raw_score: Optional[float]) -> float:
    """Return dashboard-facing normalized score (clamped 0–100). Safe fallback when missing."""
    if raw_score is None:
        return NORMALIZED_SCORE_MIN
    return clamp_normalized(raw_score, NORMALIZED_SCORE_MIN, NORMALIZED_SCORE_MAX)


def score_to_priority_band(raw_score: Optional[float]) -> str:
    """Return priority band from raw score. Deterministic."""
    return priority_band_from_score(raw_score)


def build_supporting_signal_hints(ranking: Optional[Dict[str, Any]]) -> List[str]:
    """
    Build short, explainable hints from persisted ranking row.
    Uses demand_score, competition_score, trend_score when present.
    """
    if not ranking or not isinstance(ranking, dict):
        return []
    hints: List[str] = []
    demand = ranking.get("demand_score")
    if demand is not None:
        try:
            d = float(demand)
            if d >= 60:
                hints.append("demand_strong")
            elif d >= 40:
                hints.append("demand_moderate")
        except (TypeError, ValueError):
            pass
    comp = ranking.get("competition_score")
    if comp is not None:
        try:
            c = float(comp)
            if c > 70:
                hints.append("competition_high")
            elif c < 40:
                hints.append("competition_low")
        except (TypeError, ValueError):
            pass
    trend = ranking.get("trend_score")
    if trend is not None:
        try:
            t = float(trend)
            if t >= 60:
                hints.append("trend_positive")
            elif t < 40:
                hints.append("trend_weak")
        except (TypeError, ValueError):
            pass
    return hints[:5]
