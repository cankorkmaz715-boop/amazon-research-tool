"""
Trend scoring v2. Step 87 – evaluate clusters/niche candidates using trend engine signals.
Combines review growth, rating movement, price trend, rank/BSR into a compact trend score.
Rule-based, explainable; extensible for advanced trend analysis.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("trend.scoring")


def _gather_trend_signals(
    cluster: Dict[str, Any],
    asin_to_id: Dict[str, int],
    trends_by_id: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate trend engine outputs for one cluster."""
    member_asins = cluster.get("member_asins") or []
    asin_ids = [asin_to_id[a] for a in member_asins if asin_to_id.get(a)]
    n = len(asin_ids) or 1

    review_rising = 0
    rating_rising = 0
    price_falling = 0
    rank_improving = 0
    review_stable = 0
    rating_stable = 0
    price_stable = 0

    for aid in asin_ids:
        t = trends_by_id.get(aid) or {}
        if (t.get("review_count") or {}).get("trend") == "rising":
            review_rising += 1
        elif (t.get("review_count") or {}).get("trend") == "stable":
            review_stable += 1
        if (t.get("rating") or {}).get("trend") == "rising":
            rating_rising += 1
        elif (t.get("rating") or {}).get("trend") == "stable":
            rating_stable += 1
        if (t.get("price") or {}).get("trend") == "falling":
            price_falling += 1
        elif (t.get("price") or {}).get("trend") == "stable":
            price_stable += 1
        if (t.get("rank") or {}).get("trend") == "rising":
            rank_improving += 1

    return {
        "member_count": n,
        "review_rising_count": review_rising,
        "rating_rising_count": rating_rising,
        "price_falling_count": price_falling,
        "rank_improving_count": rank_improving,
        "review_stable_count": review_stable,
        "rating_stable_count": rating_stable,
        "price_stable_count": price_stable,
    }


def _compute_trend_score(signals: Dict[str, Any]) -> tuple:
    """
    Rule-based trend score 0–100 from trend engine signals. Returns (score, explanation).
    Weights: review growth, rating movement, price trend, rank movement.
    """
    score = 0.0
    parts = []

    n = max(1, signals.get("member_count") or 1)
    review_rise = signals.get("review_rising_count") or 0
    rating_rise = signals.get("rating_rising_count") or 0
    price_fall = signals.get("price_falling_count") or 0
    rank_improve = signals.get("rank_improving_count") or 0

    score += (review_rise / n) * 30.0  # review growth
    score += (rating_rise / n) * 25.0  # rating movement
    score += (price_fall / n) * 25.0    # price trend (falling = positive for opportunity)
    score += (rank_improve / n) * 20.0 # rank/BSR movement
    parts.append(f"review↑{review_rise} rating↑{rating_rise} price↓{price_fall} rank↑{rank_improve}")

    score = max(0.0, min(100.0, score))
    explanation = f"trend_score={score:.0f}: " + ", ".join(parts)
    return score, explanation


def score_trends(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Score clusters by aggregated trend engine signals. Uses review growth, rating movement,
    price trend, rank/BSR movement. Returns { trend_results, summary } with trend_score,
    explanation, trend_signals per cluster.
    """
    if not clusters:
        return {"trend_results": [], "summary": {"total": 0}}

    all_asins = set()
    for c in clusters:
        all_asins.update(c.get("member_asins") or [])
    if asin_pool:
        all_asins &= set(asin_pool)
    all_asins = list(all_asins)

    asin_to_id: Dict[str, int] = {}
    trends_by_id: Dict[int, Dict[str, Any]] = {}

    if use_db and all_asins:
        try:
            from amazon_research.db import get_asin_id
            from amazon_research.trend import get_trends_for_asin
            for a in all_asins:
                aid = get_asin_id(a)
                if aid:
                    asin_to_id[a] = aid
            for aid in asin_to_id.values():
                try:
                    trends_by_id[aid] = get_trends_for_asin(aid)
                except Exception:
                    trends_by_id[aid] = {}
        except Exception as e:
            logger.debug("score_trends: %s", e)

    trend_results: List[Dict[str, Any]] = []
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id") or ""
        signals = _gather_trend_signals(cluster, asin_to_id, trends_by_id)
        score, explanation = _compute_trend_score(signals)
        trend_results.append({
            "cluster_id": cluster_id,
            "trend_score": round(score, 1),
            "explanation": explanation,
            "trend_signals": signals,
        })

    return {
        "trend_results": trend_results,
        "summary": {"total": len(trend_results)},
    }
