"""
Demand signal aggregator. Step 86 – aggregate demand-related signals for clusters/niche candidates.
Uses trend engine, niche context, cluster breadth, repeated appearance. Rule-based, explainable.
Extensible for opportunity and market scoring.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("demand.aggregator")


def _gather_demand_signals(
    cluster: Dict[str, Any],
    asin_to_id: Dict[str, int],
    trends_by_id: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate demand-related signals for one cluster."""
    member_asins = cluster.get("member_asins") or []
    rationale = cluster.get("rationale") or {}
    signals = rationale.get("signals") or {}

    cluster_breadth = len(member_asins)  # product count / cluster size
    has_category_context = bool(signals.get("category_context"))
    has_keyword_context = bool(signals.get("keyword_context"))
    repeated_appearance = has_category_context and has_keyword_context  # appears in both
    context_count = sum([has_category_context, has_keyword_context, bool(signals.get("co_occurrence"))])

    asin_ids = [asin_to_id[a] for a in member_asins if asin_to_id.get(a)]
    n = len(asin_ids) or 1

    review_trend_rising = 0
    rating_trend_rising = 0
    price_trend_falling = 0
    rank_trend_improving = 0

    for aid in asin_ids:
        t = trends_by_id.get(aid) or {}
        if (t.get("review_count") or {}).get("trend") == "rising":
            review_trend_rising += 1
        if (t.get("rating") or {}).get("trend") == "rising":
            rating_trend_rising += 1
        if (t.get("price") or {}).get("trend") == "falling":
            price_trend_falling += 1
        if (t.get("rank") or {}).get("trend") == "rising":  # better rank = rising BSR improvement
            rank_trend_improving += 1

    return {
        "cluster_breadth": cluster_breadth,
        "has_category_context": has_category_context,
        "has_keyword_context": has_keyword_context,
        "repeated_appearance": repeated_appearance,
        "context_count": context_count,
        "review_trend_rising_count": review_trend_rising,
        "rating_trend_rising_count": rating_trend_rising,
        "price_trend_falling_count": price_trend_falling,
        "rank_trend_improving_count": rank_trend_improving,
        "member_count": n,
    }


def _compute_demand_score(signals: Dict[str, Any]) -> tuple:
    """
    Rule-based demand score 0–100 (higher = stronger demand signals). Returns (score, level, explanation).
    """
    score = 0.0
    parts = []

    breadth = signals.get("cluster_breadth") or 0
    breadth_norm = min(1.0, breadth / 12.0) * 25.0  # cluster breadth
    score += breadth_norm
    parts.append(f"breadth={breadth}")

    n = max(1, signals.get("member_count") or 1)
    review_rise = signals.get("review_trend_rising_count") or 0
    rating_rise = signals.get("rating_trend_rising_count") or 0
    price_fall = signals.get("price_trend_falling_count") or 0
    rank_improve = signals.get("rank_trend_improving_count") or 0

    score += (review_rise / n) * 25.0  # review count growth
    score += (rating_rise / n) * 15.0  # rating trend
    score += (price_fall / n) * 10.0
    score += (rank_improve / n) * 10.0
    parts.append(f"trends(r{review_rise}r{rating_rise}p{price_fall}k{rank_improve})")

    if signals.get("repeated_appearance"):
        score += 15.0
        parts.append("repeated_appearance")
    else:
        ctx = signals.get("context_count") or 0
        if ctx > 0:
            score += min(15.0, ctx * 5.0)
            parts.append(f"contexts={ctx}")

    score = max(0.0, min(100.0, score))

    if score < 33:
        level = "low"
    elif score < 66:
        level = "medium"
    else:
        level = "high"

    explanation = "; ".join(parts)
    return score, level, explanation


def aggregate_demand(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Aggregate demand signals per cluster. Uses trend engine, niche context, cluster breadth,
    repeated appearance across category/keyword. Returns { demand_results, summary } with
    demand_score, demand_level, explanation, demand_signals per cluster.
    """
    if not clusters:
        return {"demand_results": [], "summary": {"total": 0}}

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
            logger.debug("aggregate_demand: %s", e)

    demand_results: List[Dict[str, Any]] = []
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id") or ""
        signals = _gather_demand_signals(cluster, asin_to_id, trends_by_id)
        score, level, explanation = _compute_demand_score(signals)
        demand_results.append({
            "cluster_id": cluster_id,
            "demand_score": round(score, 1),
            "demand_level": level,
            "explanation": explanation,
            "demand_signals": signals,
        })

    return {
        "demand_results": demand_results,
        "summary": {"total": len(demand_results)},
    }
