"""
Niche explorer foundation. Step 91 – browse and inspect discovered niches and product clusters.
Uses clustering, opportunity ranking, MOI, demand, competition. Backend-first; board-compatible.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("explorer.niche_explorer")


def explore_niches(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
    *,
    moi_result: Optional[Dict[str, Any]] = None,
    sort_by: str = "opportunity_index",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    List niches (product clusters) with opportunity index, demand, competition, and cluster size.
    Built from MOI (which uses fusion → ranking, demand, competition, trend, niche). If moi_result
    is omitted, runs build_market_opportunity_index. Returns { niches, summary } with entries
    in ranked order. Board-compatible (cluster_id, opportunity_index, signals).
    """
    if not clusters:
        return {"niches": [], "summary": {"total": 0}}

    if moi_result is None:
        try:
            from amazon_research.index import build_market_opportunity_index
            moi_result = build_market_opportunity_index(
                clusters,
                asin_pool=asin_pool,
                use_db=use_db,
            )
        except ImportError:
            moi_result = {"index_results": [], "summary": {"total": 0}}

    index_results = moi_result.get("index_results") or []
    cluster_by_id = {str(c.get("cluster_id", "")): c for c in clusters if c.get("cluster_id") is not None}

    niches: List[Dict[str, Any]] = []
    for idx in index_results:
        cid = idx.get("cluster_id") or ""
        cluster = cluster_by_id.get(cid) or {}
        member_asins = cluster.get("member_asins") or []
        label = cluster.get("label") or cid or "—"
        contrib = idx.get("contributing_signals") or {}
        opportunity_index = idx.get("market_opportunity_index")
        if opportunity_index is None:
            opportunity_index = 0.0
        demand_score = contrib.get("demand_score")
        if demand_score is None:
            demand_score = 0.0
        competition_score = contrib.get("competition_score")
        if competition_score is None:
            competition_score = 0.0
        cluster_size = len(member_asins)
        niches.append({
            "niche_id": cid,
            "cluster_id": cid,
            "label": label,
            "opportunity_index": round(float(opportunity_index), 1),
            "demand_score": round(float(demand_score), 1),
            "competition_score": round(float(competition_score), 1),
            "cluster_size": cluster_size,
        })

    if sort_by == "opportunity_index":
        niches.sort(key=lambda n: (-n["opportunity_index"], n["cluster_id"]))
    elif sort_by == "demand_score":
        niches.sort(key=lambda n: (-n["demand_score"], n["cluster_id"]))
    elif sort_by == "cluster_size":
        niches.sort(key=lambda n: (-n["cluster_size"], n["cluster_id"]))
    elif sort_by == "cluster_id":
        niches.sort(key=lambda n: n["cluster_id"])

    if limit is not None and limit > 0:
        niches = niches[:limit]

    return {
        "niches": niches,
        "summary": {"total": len(niches)},
    }
