"""
Trend engine foundation v1. Step 80 – rule-based trend signals from historical metrics.
Lightweight, explainable: rising, falling, stable, noisy, insufficient_data.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("trend.engine")

TREND_RISING = "rising"
TREND_FALLING = "falling"
TREND_STABLE = "stable"
TREND_NOISY = "noisy"
TREND_INSUFFICIENT = "insufficient_data"


def _numeric_series(rows: List[dict], key: str) -> List[float]:
    """Extract non-None numeric values in order."""
    out = []
    for r in rows:
        v = r.get(key)
        if v is not None:
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                pass
    return out


def _compute_trend(
    values: List[float],
    *,
    pct_threshold: float = 5.0,
    absolute_threshold: Optional[float] = None,
    min_points: int = 2,
) -> tuple:
    """
    Rule-based trend from value series. Returns (trend, explanation).
    If absolute_threshold is set (e.g. for rating 0–5), use absolute diff; else use pct.
    """
    if len(values) < min_points:
        return (
            TREND_INSUFFICIENT,
            f"need at least {min_points} points, got {len(values)}",
        )
    first, last = values[0], values[-1]
    n = len(values)

    if absolute_threshold is not None:
        diff = last - first
        if diff >= absolute_threshold:
            return (TREND_RISING, f"absolute change {diff:.2f} (first={first:.2f}, last={last:.2f})")
        if diff <= -absolute_threshold:
            return (TREND_FALLING, f"absolute change {diff:.2f} (first={first:.2f}, last={last:.2f})")
        return (TREND_STABLE, f"absolute change {diff:.2f} within threshold {absolute_threshold}")
    # Percentage-based
    if first is None or first == 0:
        return (TREND_STABLE, "no baseline for percentage")
    change_pct = (last - first) / first * 100
    if change_pct >= pct_threshold:
        return (TREND_RISING, f"change {change_pct:.1f}% ({n} points)")
    if change_pct <= -pct_threshold:
        return (TREND_FALLING, f"change {change_pct:.1f}% ({n} points)")
    return (TREND_STABLE, f"change {change_pct:.1f}% within ±{pct_threshold}%")


def _trend_insufficient(reason: str = "DB not available") -> Dict[str, Any]:
    return {
        "trend": TREND_INSUFFICIENT,
        "value_first": None,
        "value_last": None,
        "points": 0,
        "explanation": reason,
    }


def get_price_trend(
    asin_id: int,
    limit: int = 100,
    pct_threshold: float = 5.0,
) -> Dict[str, Any]:
    """Compute price trend from price_history. Returns trend, value_first, value_last, points, explanation."""
    try:
        from amazon_research.db.persistence import get_price_history
    except ImportError:
        return _trend_insufficient()
    try:
        rows = get_price_history(asin_id, limit=limit)
    except Exception as e:
        logger.debug("get_price_trend DB error: %s", e)
        return _trend_insufficient(reason="DB unavailable")
    values = _numeric_series(rows, "price")
    if len(values) < 2:
        return {
            "trend": TREND_INSUFFICIENT,
            "value_first": values[0] if values else None,
            "value_last": values[-1] if values else None,
            "points": len(values),
            "explanation": f"need at least 2 points, got {len(values)}",
        }
    trend, explanation = _compute_trend(values, pct_threshold=pct_threshold)
    return {
        "trend": trend,
        "value_first": values[0],
        "value_last": values[-1],
        "points": len(values),
        "explanation": explanation,
    }


def get_review_count_trend(
    asin_id: int,
    limit: int = 100,
    pct_threshold: float = 5.0,
) -> Dict[str, Any]:
    """Compute review count trend from review_history."""
    try:
        from amazon_research.db.persistence import get_review_history
    except ImportError:
        return _trend_insufficient()
    try:
        rows = get_review_history(asin_id, limit=limit)
    except Exception as e:
        logger.debug("get_review_count_trend DB error: %s", e)
        return _trend_insufficient(reason="DB unavailable")
    values = _numeric_series(rows, "review_count")
    if len(values) < 2:
        return {
            "trend": TREND_INSUFFICIENT,
            "value_first": values[0] if values else None,
            "value_last": values[-1] if values else None,
            "points": len(values),
            "explanation": f"need at least 2 points, got {len(values)}",
        }
    trend, explanation = _compute_trend(values, pct_threshold=pct_threshold)
    return {
        "trend": trend,
        "value_first": values[0],
        "value_last": values[-1],
        "points": len(values),
        "explanation": explanation,
    }


def get_rating_trend(
    asin_id: int,
    limit: int = 100,
    absolute_threshold: float = 0.2,
) -> Dict[str, Any]:
    """Compute rating trend from review_history (0–5 scale). Uses absolute difference."""
    try:
        from amazon_research.db.persistence import get_review_history
    except ImportError:
        return _trend_insufficient()
    try:
        rows = get_review_history(asin_id, limit=limit)
    except Exception as e:
        logger.debug("get_rating_trend DB error: %s", e)
        return _trend_insufficient(reason="DB unavailable")
    values = _numeric_series(rows, "rating")
    if len(values) < 2:
        return {
            "trend": TREND_INSUFFICIENT,
            "value_first": values[0] if values else None,
            "value_last": values[-1] if values else None,
            "points": len(values),
            "explanation": f"need at least 2 points, got {len(values)}",
        }
    trend, explanation = _compute_trend(
        values,
        absolute_threshold=absolute_threshold,
    )
    return {
        "trend": trend,
        "value_first": values[0],
        "value_last": values[-1],
        "points": len(values),
        "explanation": explanation,
    }


def _parse_bsr_to_rank(bsr: Optional[str]) -> Optional[float]:
    """Extract a numeric rank from BSR text (e.g. '1,234 in Electronics' -> 1234.0). Lower = better."""
    if not bsr or not isinstance(bsr, str):
        return None
    import re
    # First number in string (with optional commas)
    m = re.search(r"[\d,]+", bsr.strip())
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except (ValueError, TypeError):
        return None


def get_rank_trend(
    asin_id: int,
    limit: int = 100,
    pct_threshold: float = 5.0,
) -> Dict[str, Any]:
    """
    BSR/rank trend from bsr_history (Step 101). Uses numeric rank extracted from BSR text.
    Rising = rank value increased (worse position), falling = rank value decreased (improved).
    """
    try:
        from amazon_research.db.persistence import get_bsr_history
    except ImportError:
        return _trend_insufficient(reason="DB not available")
    try:
        rows = get_bsr_history(asin_id, limit=limit)
    except Exception as e:
        logger.debug("get_rank_trend DB error: %s", e)
        return _trend_insufficient(reason="DB unavailable")
    values = []
    for r in rows:
        v = _parse_bsr_to_rank(r.get("bsr"))
        if v is not None:
            values.append(v)
    if len(values) < 2:
        return {
            "trend": TREND_INSUFFICIENT,
            "value_first": values[0] if values else None,
            "value_last": values[-1] if values else None,
            "points": len(values),
            "explanation": "need at least 2 BSR points, got %s" % len(values),
        }
    trend, explanation = _compute_trend(values, pct_threshold=pct_threshold)
    return {
        "trend": trend,
        "value_first": values[0],
        "value_last": values[-1],
        "points": len(values),
        "explanation": explanation,
    }


def get_trends_for_asin(
    asin_id: int,
    price_limit: int = 100,
    review_limit: int = 100,
) -> Dict[str, Any]:
    """
    Aggregate trend outputs for one ASIN: price, review_count, rating, rank.
    Compact, explainable structure for scoring and opportunity ranking.
    """
    price = get_price_trend(asin_id, limit=price_limit)
    review = get_review_count_trend(asin_id, limit=review_limit)
    rating = get_rating_trend(asin_id, limit=review_limit)
    rank = get_rank_trend(asin_id)
    return {
        "asin_id": asin_id,
        "price": price,
        "review_count": review,
        "rating": rating,
        "rank": rank,
    }
