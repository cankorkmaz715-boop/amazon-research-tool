"""
Opportunity ranking v2. Step 82 – score product clusters using trend, niche, size, review, rating, price.
Rule-based, explainable; outputs ranked list of opportunity candidates.
"""
import math
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("ranking.opportunity_ranking")


def _gather_cluster_signals(
    cluster: Dict[str, Any],
    asin_to_id: Dict[str, int],
    metrics_by_id: Dict[int, Dict[str, Any]],
    trends_by_id: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build explainable signals for one cluster from members' metrics and trends."""
    member_asins = cluster.get("member_asins") or []
    rationale = cluster.get("rationale") or {}
    signals = rationale.get("signals") or {}

    asin_ids = [asin_to_id[a] for a in member_asins if asin_to_id.get(a)]
    cluster_size = len(member_asins)
    has_niche_context = bool(
        signals.get("category_context") or signals.get("keyword_context") or signals.get("co_occurrence")
    )

    ratings = []
    review_counts = []
    prices = []
    review_trend_rising = 0
    rating_trend_rising = 0
    price_trend_falling = 0

    for aid in asin_ids:
        m = metrics_by_id.get(aid) or {}
        if m.get("rating") is not None:
            ratings.append(float(m["rating"]))
        if m.get("review_count") is not None:
            review_counts.append(int(m["review_count"]))
        if m.get("price") is not None:
            prices.append(float(m["price"]))
        t = trends_by_id.get(aid) or {}
        if (t.get("review_count") or {}).get("trend") == "rising":
            review_trend_rising += 1
        if (t.get("rating") or {}).get("trend") == "rising":
            rating_trend_rising += 1
        if (t.get("price") or {}).get("trend") == "falling":
            price_trend_falling += 1

    n = len(asin_ids) or 1
    return {
        "cluster_size": cluster_size,
        "member_count_with_metrics": len(asin_ids),
        "has_niche_context": has_niche_context,
        "avg_rating": sum(ratings) / len(ratings) if ratings else None,
        "avg_review_count": sum(review_counts) / len(review_counts) if review_counts else None,
        "avg_price": sum(prices) / len(prices) if prices else None,
        "review_trend_rising_count": review_trend_rising,
        "rating_trend_rising_count": rating_trend_rising,
        "price_trend_falling_count": price_trend_falling,
        "rationale_signals": signals,
    }


def _compute_cluster_score(signals: Dict[str, Any]) -> tuple:
    """
    Rule-based opportunity score in [0, 100]. Returns (score, explanation).
    Weights: cluster size, niche context, avg rating, review count, trend bonuses.
    """
    score = 0.0
    parts = []

    cluster_size = signals.get("cluster_size") or 0
    size_norm = min(1.0, cluster_size / 10.0)  # cap at 10 members
    score += size_norm * 15.0
    parts.append(f"size={cluster_size}({size_norm * 15:.0f})")

    if signals.get("has_niche_context"):
        score += 15.0
        parts.append("niche(+15)")
    else:
        score += 5.0
        parts.append("no_niche(+5)")

    avg_rating = signals.get("avg_rating")
    if avg_rating is not None:
        r_norm = max(0, min(1.0, (avg_rating - 3.0) / 2.0))  # 3-5 -> 0-1
        score += r_norm * 20.0
        parts.append(f"rating={avg_rating:.1f}(+{r_norm * 20:.0f})")

    avg_review = signals.get("avg_review_count")
    if avg_review is not None:
        rev_norm = min(1.0, math.log1p(avg_review) / 5.0)  # log scale
        score += rev_norm * 15.0
        parts.append(f"reviews~{avg_review:.0f}(+{rev_norm * 15:.0f})")

    n = max(1, signals.get("member_count_with_metrics") or 1)
    review_rising = signals.get("review_trend_rising_count") or 0
    rating_rising = signals.get("rating_trend_rising_count") or 0
    price_falling = signals.get("price_trend_falling_count") or 0
    score += (review_rising / n) * 15.0
    score += (rating_rising / n) * 10.0
    score += (price_falling / n) * 10.0
    parts.append(f"trends(r{review_rising}r{rating_rising}p{price_falling})")

    score = max(0.0, min(100.0, score))
    return score, "; ".join(parts)


def rank_cluster_opportunities(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Score and rank product clusters by opportunity. Uses trend engine, metrics, cluster size, niche context.
    Returns { ranked_candidates, summary } with score, signals_used, explanation per candidate.
    """
    if not clusters:
        return {"ranked_candidates": [], "summary": {"total": 0}}

    try:
        from amazon_research.db import get_asin_id, get_product_metrics_by_asin_ids
        from amazon_research.trend import get_trends_for_asin
    except ImportError:
        logger.warning("opportunity_ranking: DB or trend not available")
        ranked = [
            {
                "cluster_id": c.get("cluster_id", ""),
                "score": 0.0,
                "signals_used": {},
                "explanation": "DB/trend unavailable",
            }
            for c in clusters
        ]
        return {"ranked_candidates": ranked, "summary": {"total": len(ranked)}}

    all_asins = set()
    for c in clusters:
        all_asins.update(c.get("member_asins") or [])
    if asin_pool:
        all_asins &= set(asin_pool)
    all_asins = list(all_asins)

    asin_to_id: Dict[str, int] = {}
    if use_db:
        try:
            for a in all_asins:
                aid = get_asin_id(a)
                if aid:
                    asin_to_id[a] = aid
            asin_ids = list(asin_to_id.values())
            metrics_list = get_product_metrics_by_asin_ids(asin_ids) if asin_ids else []
            metrics_by_id = {m["asin_id"]: m for m in metrics_list}
            trends_by_id = {}
            for aid in asin_ids:
                try:
                    trends_by_id[aid] = get_trends_for_asin(aid)
                except Exception:
                    trends_by_id[aid] = {}
        except Exception as e:
            logger.debug("rank_cluster_opportunities: %s", e)
            metrics_by_id = {}
            trends_by_id = {}
    else:
        metrics_by_id = {}
        trends_by_id = {}

    scored: List[Dict[str, Any]] = []
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id") or ""
        signals = _gather_cluster_signals(
            cluster,
            asin_to_id,
            metrics_by_id,
            trends_by_id,
        )
        score, explanation = _compute_cluster_score(signals)
        scored.append({
            "cluster_id": cluster_id,
            "score": round(score, 1),
            "signals_used": {
                "cluster_size": signals.get("cluster_size"),
                "has_niche_context": signals.get("has_niche_context"),
                "avg_rating": signals.get("avg_rating"),
                "avg_review_count": signals.get("avg_review_count"),
                "avg_price": signals.get("avg_price"),
                "review_trend_rising_count": signals.get("review_trend_rising_count"),
                "rating_trend_rising_count": signals.get("rating_trend_rising_count"),
                "price_trend_falling_count": signals.get("price_trend_falling_count"),
            },
            "explanation": explanation,
        })

    scored.sort(key=lambda x: (-x["score"], x["cluster_id"]))
    return {
        "ranked_candidates": scored,
        "summary": {"total": len(scored)},
    }
