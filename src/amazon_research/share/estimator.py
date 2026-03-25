"""
Market share estimator foundation. Step 97 – proxy share weights for cluster members.
Uses review count concentration, rating strength, cluster member weighting. Rule-based, explainable.
"""
import math
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("share.estimator")


def _estimate_weights(
    member_asins: List[str],
    asin_to_id: Dict[str, int],
    metrics_by_id: Dict[int, Dict[str, Any]],
) -> tuple:
    """
    Compute per-member share weights from review count and rating. Returns (weights_dict, explanation_parts).
    Weight proxy: log1p(review_count) * (0.5 + 0.1 * rating) so more reviews and higher rating = higher weight.
    """
    weights: Dict[str, float] = {}
    parts: List[str] = []

    for asin in member_asins:
        aid = asin_to_id.get(asin)
        m = (metrics_by_id.get(aid) or {}) if aid else {}
        review_count = m.get("review_count")
        rating = m.get("rating")
        if review_count is not None:
            try:
                rc = max(0, int(review_count))
            except (TypeError, ValueError):
                rc = 0
        else:
            rc = 0
        if rating is not None:
            try:
                rt = max(0.0, min(5.0, float(rating)))
            except (TypeError, ValueError):
                rt = 0.0
        else:
            rt = 0.0
        raw = math.log1p(rc) * (0.5 + 0.1 * rt)
        weights[asin] = max(0.0, raw)

    total = sum(weights.values())
    if total > 0:
        for k in weights:
            weights[k] = round(weights[k] / total, 4)
        parts.append("review+rating")
    else:
        n = len(member_asins) or 1
        uniform = 1.0 / n
        for a in member_asins:
            weights[a] = round(uniform, 4)
        parts.append("uniform")

    return weights, parts


def _concentration_summary(weights: Dict[str, float]) -> Dict[str, Any]:
    """Herfindahl-style concentration and top share."""
    if not weights:
        return {"hhi": 0.0, "top_share": 0.0, "top_asin": None}
    vals = list(weights.values())
    hhi = sum(w * w for w in vals)
    sorted_items = sorted(weights.items(), key=lambda x: -x[1])
    top_asin = sorted_items[0][0] if sorted_items else None
    top_share = sorted_items[0][1] if sorted_items else 0.0
    return {"hhi": round(hhi, 4), "top_share": round(top_share, 4), "top_asin": top_asin}


def estimate_market_share(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Estimate market share weights for each cluster member using review count, rating, and uniform fallback.
    Returns { estimates, summary } with cluster_id, member_share_weights, concentration_summary,
    explanation per cluster. No real sales data; proxy only.
    """
    if not clusters:
        return {"estimates": [], "summary": {"total": 0}}

    all_asins = set()
    for c in clusters:
        all_asins.update(c.get("member_asins") or [])
    if asin_pool:
        all_asins &= set(asin_pool)
    all_asins = list(all_asins)

    asin_to_id: Dict[str, int] = {}
    metrics_by_id: Dict[int, Dict[str, Any]] = {}
    if use_db and all_asins:
        try:
            from amazon_research.db import get_asin_id, get_product_metrics_by_asin_ids
            for a in all_asins:
                aid = get_asin_id(a)
                if aid:
                    asin_to_id[a] = aid
            asin_ids = list(asin_to_id.values())
            if asin_ids:
                metrics_list = get_product_metrics_by_asin_ids(asin_ids)
                metrics_by_id = {m["asin_id"]: m for m in metrics_list}
        except Exception as e:
            logger.debug("estimate_market_share: %s", e)

    estimates: List[Dict[str, Any]] = []
    for cluster in clusters:
        cid = cluster.get("cluster_id") or ""
        member_asins = cluster.get("member_asins") or []
        weights, expl_parts = _estimate_weights(member_asins, asin_to_id, metrics_by_id)
        concentration = _concentration_summary(weights)
        explanation = "share weights: " + ", ".join(expl_parts) + "; concentration HHI=" + str(concentration.get("hhi", 0))
        estimates.append({
            "cluster_id": cid,
            "niche_id": cid,
            "member_share_weights": weights,
            "concentration_summary": concentration,
            "explanation": explanation,
        })

    return {
        "estimates": estimates,
        "summary": {"total": len(estimates)},
    }
