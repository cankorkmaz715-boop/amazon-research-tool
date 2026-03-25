"""
Niche scoring v2. Step 84 – evaluate niche candidates or clusters; niche score + compact explanation.
Reuses opportunity ranking, clustering, niche detector, trend signals. Rule-based, explainable.
Extensible for demand/competition sub-scores later.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("niche.scoring")


def _compact_explanation(signals_used: Dict[str, Any], score: float) -> str:
    """Build a short, niche-focused explanation from contributing signals."""
    parts = []
    size = signals_used.get("cluster_size")
    if size is not None:
        parts.append(f"size={size}")
    if signals_used.get("has_niche_context"):
        parts.append("niche context")
    avg_r = signals_used.get("avg_rating")
    if avg_r is not None:
        parts.append(f"rating≈{avg_r:.1f}")
    avg_rev = signals_used.get("avg_review_count")
    if avg_rev is not None:
        parts.append(f"reviews≈{avg_rev:.0f}")
    r_rise = signals_used.get("review_trend_rising_count") or 0
    rt_rise = signals_used.get("rating_trend_rising_count") or 0
    p_fall = signals_used.get("price_trend_falling_count") or 0
    if r_rise or rt_rise or p_fall:
        parts.append(f"trends(r{r_rise}/r{rt_rise}/p{p_fall})")
    if not parts:
        return f"niche score {score:.0f}"
    return f"{score:.0f}: " + ", ".join(parts)


def score_niches(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Score niche candidates or product clusters at niche level.
    Reuses opportunity ranking; produces niche_score and compact explanation per cluster.
    Returns { scored_niches, summary }. Each item: cluster_id, niche_score, explanation, contributing_signals.
    """
    if not clusters:
        return {"scored_niches": [], "summary": {"total": 0}}

    try:
        from amazon_research.ranking import rank_cluster_opportunities
    except ImportError:
        logger.warning("niche scoring: ranking not available")
        scored = [
            {
                "cluster_id": c.get("cluster_id", ""),
                "niche_score": 0.0,
                "explanation": "ranking unavailable",
                "contributing_signals": {},
            }
            for c in clusters
        ]
        return {"scored_niches": scored, "summary": {"total": len(scored)}}

    ranking_result = rank_cluster_opportunities(
        clusters,
        asin_pool=asin_pool,
        use_db=use_db,
    )
    ranked = ranking_result.get("ranked_candidates") or []

    scored_niches: List[Dict[str, Any]] = []
    for cand in ranked:
        cluster_id = cand.get("cluster_id") or ""
        score = cand.get("score")
        if score is None:
            score = 0.0
        signals_used = cand.get("signals_used") or {}
        explanation = _compact_explanation(signals_used, score)
        scored_niches.append({
            "cluster_id": cluster_id,
            "niche_score": round(float(score), 1),
            "explanation": explanation,
            "contributing_signals": signals_used,
        })

    return {
        "scored_niches": scored_niches,
        "summary": {"total": len(scored_niches)},
    }
