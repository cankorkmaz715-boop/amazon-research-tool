"""
Opportunity signal fusion. Step 88 – combine demand, competition, trend, niche, ranking into one score.
Rule-based, explainable; compatible with market opportunity board.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("fusion.opportunity_fusion")


def fuse_opportunity_signals(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
    *,
    ranking_result: Optional[Dict[str, Any]] = None,
    niche_result: Optional[Dict[str, Any]] = None,
    competition_result: Optional[Dict[str, Any]] = None,
    demand_result: Optional[Dict[str, Any]] = None,
    trend_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fuse opportunity signals from ranking, niche, competition, demand, trend into a single score per cluster.
    If any result is omitted, it is computed. Weights: ranking 0.25, demand 0.25, (100-competition) 0.25,
    trend 0.125, niche 0.125. Returns { fused_results, summary } with fused_opportunity_score,
    explanation, contributing_signals per cluster. Board-compatible (cluster_id, score, signals).
    """
    if not clusters:
        return {"fused_results": [], "summary": {"total": 0}}

    if ranking_result is None:
        try:
            from amazon_research.ranking import rank_cluster_opportunities
            ranking_result = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=use_db)
        except ImportError:
            ranking_result = {}
    ranked = ranking_result.get("ranked_candidates") or []

    if niche_result is None:
        try:
            from amazon_research.niche import score_niches
            niche_result = score_niches(clusters, asin_pool=asin_pool, use_db=use_db)
        except ImportError:
            niche_result = {}
    scored_niches = niche_result.get("scored_niches") or []

    if competition_result is None:
        try:
            from amazon_research.competition import estimate_competition
            competition_result = estimate_competition(clusters, asin_pool=asin_pool, use_db=use_db)
        except ImportError:
            competition_result = {}
    estimates = competition_result.get("estimates") or []

    if demand_result is None:
        try:
            from amazon_research.demand import aggregate_demand
            demand_result = aggregate_demand(clusters, asin_pool=asin_pool, use_db=use_db)
        except ImportError:
            demand_result = {}
    demand_results = demand_result.get("demand_results") or []

    if trend_result is None:
        try:
            from amazon_research.trend import score_trends
            trend_result = score_trends(clusters, asin_pool=asin_pool, use_db=use_db)
        except ImportError:
            trend_result = {}
    trend_results = trend_result.get("trend_results") or []

    by_id = lambda key, items: {x[key]: x for x in items}
    rank_by_id = by_id("cluster_id", ranked)
    niche_by_id = by_id("cluster_id", scored_niches)
    comp_by_id = by_id("cluster_id", estimates)
    demand_by_id = by_id("cluster_id", demand_results)
    trend_by_id = by_id("cluster_id", trend_results)

    w_rank, w_demand, w_comp, w_trend, w_niche = 0.25, 0.25, 0.25, 0.125, 0.125

    fused_results: List[Dict[str, Any]] = []
    for c in clusters:
        cid = c.get("cluster_id") or ""
        r = rank_by_id.get(cid) or {}
        n = niche_by_id.get(cid) or {}
        comp = comp_by_id.get(cid) or {}
        d = demand_by_id.get(cid) or {}
        t = trend_by_id.get(cid) or {}

        rank_s = (r.get("score") if isinstance(r.get("score"), (int, float)) else None) or 0.0
        niche_s = (n.get("niche_score") if isinstance(n.get("niche_score"), (int, float)) else None) or 0.0
        comp_s = (comp.get("competition_score") if isinstance(comp.get("competition_score"), (int, float)) else None) or 0.0
        demand_s = (d.get("demand_score") if isinstance(d.get("demand_score"), (int, float)) else None) or 0.0
        trend_s = (t.get("trend_score") if isinstance(t.get("trend_score"), (int, float)) else None) or 0.0

        # Opportunity = high demand, low competition, positive trends; competition inverted
        comp_inv = 100.0 - min(100.0, max(0.0, comp_s))
        fused = rank_s * w_rank + demand_s * w_demand + comp_inv * w_comp + trend_s * w_trend + niche_s * w_niche
        fused = max(0.0, min(100.0, round(fused, 1)))

        contributing = {
            "ranking_score": round(rank_s, 1),
            "demand_score": round(demand_s, 1),
            "competition_score": round(comp_s, 1),
            "competition_inverted": round(comp_inv, 1),
            "trend_score": round(trend_s, 1),
            "niche_score": round(niche_s, 1),
        }
        explanation = f"fused={fused:.0f} (rank={rank_s:.0f} demand={demand_s:.0f} 100-comp={comp_inv:.0f} trend={trend_s:.0f} niche={niche_s:.0f})"

        fused_results.append({
            "cluster_id": cid,
            "fused_opportunity_score": fused,
            "explanation": explanation,
            "contributing_signals": contributing,
        })

    fused_results.sort(key=lambda x: (-x["fused_opportunity_score"], x["cluster_id"]))
    return {
        "fused_results": fused_results,
        "summary": {"total": len(fused_results)},
    }
