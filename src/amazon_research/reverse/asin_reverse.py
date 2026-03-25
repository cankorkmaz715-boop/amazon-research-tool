"""
Reverse ASIN engine. Step 96 – reconstruct context for a single ASIN from clusters and discovery context.
Uses keyword/category scan context, cluster membership, niche/opportunity signals. Lightweight, explainable.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("reverse.asin_reverse")


def reverse_asin(
    asin: str,
    *,
    clusters: Optional[List[Dict[str, Any]]] = None,
    discovery_context: Optional[List[Dict[str, Any]]] = None,
    ranking_result: Optional[Dict[str, Any]] = None,
    moi_result: Optional[Dict[str, Any]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Reconstruct context for a single ASIN. Uses discovery_context (keyword/category scan sources),
    clusters (membership), and optional ranking/MOI for opportunity signals. No external scraping.
    Returns { input_asin, related_keywords, related_categories, cluster_associations,
    opportunity_signal_summary, product_metadata (if use_db) }.
    """
    input_asin = (asin or "").strip()
    if not input_asin:
        return {
            "input_asin": "",
            "related_keywords": [],
            "related_categories": [],
            "cluster_associations": [],
            "opportunity_signal_summary": {},
            "product_metadata": None,
        }

    related_keywords: List[str] = []
    related_categories: List[str] = []

    if discovery_context:
        for ctx in discovery_context:
            asins = [str(a).strip() for a in (ctx.get("asins") or []) if a]
            if input_asin not in asins:
                continue
            source_type = (ctx.get("source_type") or "").strip().lower()
            source_id = (ctx.get("source_id") or "").strip()
            if source_type == "keyword" and source_id and source_id not in related_keywords:
                related_keywords.append(source_id)
            elif source_type == "category" and source_id and source_id not in related_categories:
                related_categories.append(source_id)

    cluster_associations: List[Dict[str, Any]] = []
    if clusters:
        for c in clusters:
            member_asins = c.get("member_asins") or []
            if input_asin not in member_asins:
                continue
            cid = c.get("cluster_id") or ""
            label = c.get("label") or cid
            cluster_associations.append({
                "cluster_id": cid,
                "label": label,
                "cluster_size": len(member_asins),
            })

    rank_by_id = {}
    moi_by_id = {}
    if ranking_result:
        rank_by_id = {r["cluster_id"]: r for r in ranking_result.get("ranked_candidates") or []}
    if moi_result:
        moi_by_id = {m["cluster_id"]: m for m in moi_result.get("index_results") or []}

    opportunity_signal_summary: Dict[str, Any] = {}
    if cluster_associations and clusters:
        best = cluster_associations[0]
        cid = best.get("cluster_id")
        full_cluster = next((c for c in clusters if c.get("cluster_id") == cid), None)
        opp = (moi_by_id.get(cid) or {}).get("contributing_signals") or {}
        opportunity_signal_summary = {
            "opportunity_index": (moi_by_id.get(cid) or {}).get("market_opportunity_index"),
            "demand_score": opp.get("demand_score"),
            "competition_score": opp.get("competition_score"),
            "trend_score": opp.get("trend_score"),
            "niche_score": None,
            "ranking_score": (rank_by_id.get(cid) or {}).get("score"),
        }
        if full_cluster:
            try:
                from amazon_research.niche import score_niches
                scoring = score_niches([full_cluster], use_db=use_db)
                scored = scoring.get("scored_niches") or []
                if scored:
                    opportunity_signal_summary["niche_score"] = scored[0].get("niche_score")
            except Exception:
                pass
        if not any(v is not None for v in opportunity_signal_summary.values()):
            opportunity_signal_summary["source"] = "cluster_association"

    product_metadata = None
    if use_db and input_asin:
        try:
            from amazon_research.db import get_asins_metadata
            meta = get_asins_metadata([input_asin])
            if meta:
                product_metadata = meta[0]
        except Exception as e:
            logger.debug("reverse_asin: get_asins_metadata: %s", e)

    return {
        "input_asin": input_asin,
        "related_keywords": related_keywords,
        "related_categories": related_categories,
        "cluster_associations": cluster_associations,
        "opportunity_signal_summary": opportunity_signal_summary,
        "product_metadata": product_metadata,
    }
