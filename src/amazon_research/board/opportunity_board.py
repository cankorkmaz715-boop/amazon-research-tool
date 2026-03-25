"""
Market opportunity board. Step 83 – present ranked product-cluster opportunities.
Reuses opportunity ranking, clustering, niche detector, trend engine outputs.
Dashboard-friendly entries: cluster_id, label, score, core signals, member count.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("board.opportunity_board")


def _cluster_by_id(clusters: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index clusters by cluster_id."""
    return {str(c.get("cluster_id", "")): c for c in clusters if c.get("cluster_id") is not None}


def build_opportunity_board(
    clusters: List[Dict[str, Any]],
    ranking_result: Optional[Dict[str, Any]] = None,
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
    *,
    sort_by: str = "score",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a market opportunity board from clusters and (optional) ranking result.
    If ranking_result is None, runs rank_cluster_opportunities(clusters) to obtain scores.
    Each board entry: cluster_id, label, opportunity_score, core_signals, member_count.
    Dashboard-ready; extensible for filters and saved views.
    """
    if not clusters:
        return {"entries": [], "summary": {"total": 0}}

    if ranking_result is None:
        try:
            from amazon_research.ranking import rank_cluster_opportunities
            ranking_result = rank_cluster_opportunities(
                clusters,
                asin_pool=asin_pool,
                use_db=use_db,
            )
        except ImportError:
            ranking_result = {"ranked_candidates": [], "summary": {"total": 0}}

    ranked = ranking_result.get("ranked_candidates") or []
    cluster_map = _cluster_by_id(clusters)

    entries: List[Dict[str, Any]] = []
    for cand in ranked:
        cluster_id = cand.get("cluster_id") or ""
        cluster = cluster_map.get(cluster_id) or {}
        member_asins = cluster.get("member_asins") or []
        label = cluster.get("label") or cluster_id or "—"
        score = cand.get("score")
        if score is None:
            score = 0.0
        signals_used = cand.get("signals_used") or {}
        core_signals = {
            "cluster_size": signals_used.get("cluster_size") or len(member_asins),
            "has_niche_context": signals_used.get("has_niche_context"),
            "avg_rating": signals_used.get("avg_rating"),
            "avg_review_count": signals_used.get("avg_review_count"),
            "avg_price": signals_used.get("avg_price"),
            "review_trend_rising_count": signals_used.get("review_trend_rising_count"),
            "rating_trend_rising_count": signals_used.get("rating_trend_rising_count"),
            "price_trend_falling_count": signals_used.get("price_trend_falling_count"),
        }
        member_count = len(member_asins)
        entries.append({
            "cluster_id": cluster_id,
            "label": label,
            "opportunity_score": round(float(score), 1),
            "core_signals": core_signals,
            "member_count": member_count,
        })

    if sort_by == "score":
        entries.sort(key=lambda e: (-e["opportunity_score"], e["cluster_id"]))
    elif sort_by == "member_count":
        entries.sort(key=lambda e: (-e["member_count"], e["cluster_id"]))
    elif sort_by == "cluster_id":
        entries.sort(key=lambda e: e["cluster_id"])

    if limit is not None and limit > 0:
        entries = entries[:limit]

    summary = {
        "total": len(entries),
        "sort_by": sort_by,
    }
    return {
        "entries": entries,
        "summary": summary,
    }
