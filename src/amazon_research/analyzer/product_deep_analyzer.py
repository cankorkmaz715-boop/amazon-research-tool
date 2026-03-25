"""
Product deep analyzer. Step 92 – evaluate a single ASIN or product cluster with full signal aggregation.
Uses demand, competition, trend scoring, niche scoring, market opportunity index. Explainable, rule-based.
"""
from typing import Any, Dict, List, Optional, Union

from amazon_research.logging_config import get_logger

logger = get_logger("analyzer.product_deep_analyzer")


def _as_cluster(target: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize ASIN string or cluster dict into a single cluster."""
    if isinstance(target, str):
        asin = (target or "").strip()
        if not asin:
            return {"cluster_id": "empty", "member_asins": [], "label": "—"}
        return {
            "cluster_id": f"asin_{asin}",
            "member_asins": [asin],
            "label": asin,
        }
    if isinstance(target, dict) and "member_asins" in target:
        return target
    return {"cluster_id": "unknown", "member_asins": [], "label": "—"}


def _key_signals_summary(contrib: Dict[str, Any]) -> str:
    """Short explainable summary of contributing signals."""
    parts = []
    for k in ("ranking_score", "demand_score", "competition_score", "trend_score", "niche_score"):
        v = contrib.get(k)
        if v is not None:
            parts.append(f"{k}={v:.0f}")
    return "; ".join(parts) if parts else "no signals"


def deep_analyze(
    target: Union[str, Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Run deep analysis on a single ASIN or a product cluster. Aggregates demand, competition,
    trend scoring, niche scoring, and market opportunity index. Returns a single analysis result
    with product_id/cluster_id, opportunity_index, demand_score, competition_score, trend_score,
    key_signals_summary. Compatible with niche explorer and opportunity board (cluster shape).
    """
    cluster = _as_cluster(target)
    clusters = [cluster]

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
    if not index_results:
        cid = cluster.get("cluster_id") or "unknown"
        return {
            "product_id": cid,
            "cluster_id": cid,
            "opportunity_index": 0.0,
            "demand_score": 0.0,
            "competition_score": 0.0,
            "trend_score": 0.0,
            "niche_score": 0.0,
            "key_signals_summary": "no data",
        }

    idx = index_results[0]
    cid = idx.get("cluster_id") or cluster.get("cluster_id") or "unknown"
    contrib = idx.get("contributing_signals") or {}
    opportunity_index = idx.get("market_opportunity_index")
    if opportunity_index is None:
        opportunity_index = 0.0
    demand_score = contrib.get("demand_score") or 0.0
    competition_score = contrib.get("competition_score") or 0.0
    trend_score = contrib.get("trend_score") or 0.0
    niche_score = contrib.get("niche_score") or 0.0

    return {
        "product_id": cid,
        "cluster_id": cid,
        "opportunity_index": round(float(opportunity_index), 1),
        "demand_score": round(float(demand_score), 1),
        "competition_score": round(float(competition_score), 1),
        "trend_score": round(float(trend_score), 1),
        "niche_score": round(float(niche_score), 1),
        "key_signals_summary": _key_signals_summary(contrib),
        "contributing_signals": contrib,
    }


def deep_analyze_batch(
    targets: List[Union[str, Dict[str, Any]]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Run deep analysis on multiple ASINs or clusters. Returns { analyses, summary }.
    Each analysis has the same shape as deep_analyze. Ordered by opportunity_index descending.
    """
    if not targets:
        return {"analyses": [], "summary": {"total": 0}}

    clusters = [_as_cluster(t) for t in targets]
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
    analyses = []
    for i, idx in enumerate(index_results):
        cluster = clusters[i] if i < len(clusters) else {}
        cid = idx.get("cluster_id") or cluster.get("cluster_id") or "unknown"
        contrib = idx.get("contributing_signals") or {}
        analyses.append({
            "product_id": cid,
            "cluster_id": cid,
            "opportunity_index": round(float(idx.get("market_opportunity_index") or 0), 1),
            "demand_score": round(float(contrib.get("demand_score") or 0), 1),
            "competition_score": round(float(contrib.get("competition_score") or 0), 1),
            "trend_score": round(float(contrib.get("trend_score") or 0), 1),
            "niche_score": round(float(contrib.get("niche_score") or 0), 1),
            "key_signals_summary": _key_signals_summary(contrib),
            "contributing_signals": contrib,
        })

    analyses.sort(key=lambda a: (-a["opportunity_index"], a["cluster_id"]))
    return {
        "analyses": analyses,
        "summary": {"total": len(analyses)},
    }
