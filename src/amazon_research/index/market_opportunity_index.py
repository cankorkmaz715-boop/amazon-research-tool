"""
Market opportunity index (MOI). Step 89 – standardized opportunity scoring across niches and clusters.
Operates on opportunity signal fusion outputs; normalized index for cross-cluster comparison.
Rule-based, explainable; board and ranking compatible.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("index.market_opportunity_index")


def _tier_from_score(score: float) -> str:
    """Rule-based tier: high >= 66, medium 33–65, low < 33."""
    if score >= 66:
        return "high"
    if score >= 33:
        return "medium"
    return "low"


def build_market_opportunity_index(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
    *,
    fusion_result: Optional[Dict[str, Any]] = None,
    normalize_within_batch: bool = True,
) -> Dict[str, Any]:
    """
    Build market opportunity index from fusion outputs. Produces a normalized opportunity index
    per cluster (0–100) for comparison across niches and clusters. If fusion_result is omitted,
    runs fuse_opportunity_signals. When normalize_within_batch is True, also outputs batch_normalized_moi
    (best=100, worst=0) for relative comparison within the current set.
    Returns { index_results, summary } with market_opportunity_index, moi_tier, explanation,
    contributing_signals per cluster. Board and ranking compatible.
    """
    if not clusters:
        return {"index_results": [], "summary": {"total": 0}}

    if fusion_result is None:
        try:
            from amazon_research.fusion import fuse_opportunity_signals
            fusion_result = fuse_opportunity_signals(
                clusters,
                asin_pool=asin_pool,
                use_db=use_db,
            )
        except ImportError:
            fusion_result = {"fused_results": [], "summary": {"total": 0}}

    fused = fusion_result.get("fused_results") or []
    if not fused:
        return {"index_results": [], "summary": {"total": 0}}

    scores = [f["fused_opportunity_score"] for f in fused]
    min_s = min(scores)
    max_s = max(scores)
    span = max_s - min_s if (max_s - min_s) > 0 else 1.0

    index_results: List[Dict[str, Any]] = []
    for f in fused:
        cid = f.get("cluster_id") or ""
        raw = f.get("fused_opportunity_score") or 0.0
        contrib = f.get("contributing_signals") or {}
        batch_norm = round((raw - min_s) / span * 100.0, 1) if normalize_within_batch else None
        moi = raw  # absolute index (0–100), comparable across runs and niches
        tier = _tier_from_score(moi)
        explanation = f"MOI={moi:.0f} ({tier})"
        if batch_norm is not None:
            explanation += f" batch_norm={batch_norm:.0f}"
        explanation += f" (rank={contrib.get('ranking_score', 0):.0f} demand={contrib.get('demand_score', 0):.0f} comp_inv={contrib.get('competition_inverted', 0):.0f})"
        index_results.append({
            "cluster_id": cid,
            "market_opportunity_index": round(moi, 1),
            "batch_normalized_moi": batch_norm,
            "moi_tier": tier,
            "explanation": explanation,
            "contributing_signals": contrib,
        })

    index_results.sort(key=lambda x: (-x["market_opportunity_index"], x["cluster_id"]))
    return {
        "index_results": index_results,
        "summary": {"total": len(index_results), "min_moi": min_s, "max_moi": max_s},
    }
