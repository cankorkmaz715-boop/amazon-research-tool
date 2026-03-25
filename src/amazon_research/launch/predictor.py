"""
Product launch predictor foundation. Step 98 – evaluate whether entering a niche/cluster is favorable.
Uses demand, competition, market share, trend, niche scoring, MOI. Rule-based, explainable.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("launch.predictor")


def predict_launch(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
    *,
    moi_result: Optional[Dict[str, Any]] = None,
    share_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Predict launch feasibility per cluster. Aggregates demand, competition, trend, niche, opportunity index,
    and optionally market share concentration. Returns { predictions, summary } with cluster_id, launch_feasibility_score,
    main_supporting_signals, explanation. Favorable = high demand, low competition, positive trend, high opportunity.
    """
    if not clusters:
        return {"predictions": [], "summary": {"total": 0}}

    if moi_result is None:
        try:
            from amazon_research.index import build_market_opportunity_index
            moi_result = build_market_opportunity_index(
                clusters,
                asin_pool=asin_pool,
                use_db=use_db,
            )
        except ImportError:
            moi_result = {"index_results": [], "summary": {}}

    index_results = moi_result.get("index_results") or []
    moi_by_id = {r["cluster_id"]: r for r in index_results}

    share_by_id: Dict[str, Dict[str, Any]] = {}
    if share_result:
        for e in share_result.get("estimates") or []:
            cid = e.get("cluster_id")
            if cid:
                share_by_id[cid] = e
    elif use_db:
        try:
            from amazon_research.share import estimate_market_share
            share_result = estimate_market_share(clusters, asin_pool=asin_pool, use_db=True)
            for e in share_result.get("estimates") or []:
                cid = e.get("cluster_id")
                if cid:
                    share_by_id[cid] = e
        except Exception as e:
            logger.debug("predict_launch: estimate_market_share: %s", e)

    predictions: List[Dict[str, Any]] = []
    for cluster in clusters:
        cid = cluster.get("cluster_id") or ""
        moi = moi_by_id.get(cid) or {}
        contrib = moi.get("contributing_signals") or {}
        opportunity_index = moi.get("market_opportunity_index") or 0.0
        demand_score = contrib.get("demand_score") or 0.0
        competition_score = contrib.get("competition_score") or 0.0
        trend_score = contrib.get("trend_score") or 0.0
        niche_score = contrib.get("niche_score") or 0.0

        # Launch feasibility: high opportunity, demand, trend, niche; low competition
        comp_inv = 100.0 - min(100.0, max(0.0, float(competition_score)))
        feasibility = (
            0.25 * float(opportunity_index)
            + 0.25 * float(demand_score)
            + 0.20 * comp_inv
            + 0.15 * float(trend_score)
            + 0.15 * float(niche_score)
        )
        feasibility = max(0.0, min(100.0, round(feasibility, 1)))

        share_est = share_by_id.get(cid) or {}
        conc = share_est.get("concentration_summary") or {}
        hhi = conc.get("hhi") or 0.0
        if hhi > 0.25:
            feasibility = feasibility * 0.95  # slight penalty for high concentration
            feasibility = round(feasibility, 1)

        main_supporting_signals = {
            "demand_score": round(float(demand_score), 1),
            "competition_score": round(float(competition_score), 1),
            "trend_score": round(float(trend_score), 1),
            "niche_score": round(float(niche_score), 1),
            "opportunity_index": round(float(opportunity_index), 1),
            "concentration_hhi": round(float(hhi), 4) if hhi else None,
        }
        explanation = (
            f"Launch feasibility {feasibility:.0f}: demand={demand_score:.0f}, competition={competition_score:.0f} "
            f"(inverted for favorability), trend={trend_score:.0f}, niche={niche_score:.0f}, MOI={opportunity_index:.0f}."
        )
        if hhi > 0.25:
            explanation += " High concentration (HHI) slightly reduces feasibility."

        predictions.append({
            "cluster_id": cid,
            "niche_id": cid,
            "launch_feasibility_score": feasibility,
            "main_supporting_signals": main_supporting_signals,
            "explanation": explanation,
        })

    predictions.sort(key=lambda p: (-p["launch_feasibility_score"], p["cluster_id"]))
    return {
        "predictions": predictions,
        "summary": {"total": len(predictions)},
    }
