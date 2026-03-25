"""
Automated niche discovery pipeline. Step 95 – chain seeds, clustering, ranking, niche scoring.
Starts from keyword/category seeds or pre-built discovery_context + asin_pool. Lightweight, queue-friendly.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.niche_discovery")


def _build_discovery_context_from_seeds(
    seed_keywords: Optional[List[str]] = None,
    seed_category_urls: Optional[List[str]] = None,
    asin_pool: Optional[List[str]] = None,
    expand_keywords: bool = False,
) -> List[Dict[str, Any]]:
    """Build discovery_context from seed keywords and/or category URLs. Optionally expand keywords."""
    ctx: List[Dict[str, Any]] = []
    pool = list(asin_pool or [])

    if seed_keywords:
        keywords = [str(k).strip() for k in seed_keywords if k and str(k).strip()]
        if expand_keywords and keywords:
            try:
                from amazon_research.keywords import expand_keywords
                expanded = set(keywords)
                for kw in keywords:
                    out = expand_keywords(kw, max_candidates=5)
                    for c in out.get("candidates") or []:
                        exp = (c.get("expanded_keyword") or "").strip()
                        if exp:
                            expanded.add(exp)
                keywords = list(expanded)
            except Exception as e:
                logger.debug("niche_discovery: expand_keywords: %s", e)
        for kw in keywords:
            ctx.append({
                "source_type": "keyword",
                "source_id": kw,
                "asins": pool,
            })

    if seed_category_urls:
        for url in seed_category_urls:
            u = (url or "").strip()
            if not u:
                continue
            ctx.append({
                "source_type": "category",
                "source_id": u,
                "asins": pool,
            })

    return ctx


def _seed_source_from_cluster(cluster: Dict[str, Any]) -> str:
    """Infer seed source (keyword or category URL) from cluster rationale."""
    rationale = cluster.get("rationale") or {}
    signals = rationale.get("signals") or {}
    if signals.get("keyword_context"):
        return str(signals["keyword_context"].get("source_id") or "keyword")
    if signals.get("category_context"):
        return str(signals["category_context"].get("source_id") or "category")
    return cluster.get("cluster_id") or "unknown"


def _related_from_cluster(cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Related keywords/categories from cluster rationale."""
    rationale = cluster.get("rationale") or {}
    signals = rationale.get("signals") or {}
    out: Dict[str, Any] = {"keywords": [], "categories": []}
    if signals.get("keyword_context"):
        out["keywords"].append(signals["keyword_context"].get("source_id"))
    if signals.get("category_context"):
        out["categories"].append(signals["category_context"].get("source_id"))
    return out


def run_niche_discovery(
    asin_pool: Optional[List[str]] = None,
    discovery_context: Optional[List[Dict[str, Any]]] = None,
    *,
    seed_keywords: Optional[List[str]] = None,
    seed_category_urls: Optional[List[str]] = None,
    expand_keywords: bool = False,
    use_db: bool = True,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run automated niche discovery: build or use discovery_context + asin_pool, cluster, rank, niche score.
    Seeds: provide discovery_context + asin_pool directly, or seed_keywords/seed_category_urls (asin_pool
    then used for all context entries). Optionally expand_keywords. Returns { niches, summary } with
    niche_id, seed_source, related_keywords/categories, cluster_id, cluster_summary, opportunity_signals_summary.
    """
    pool = list(asin_pool or [])
    if discovery_context is None:
        discovery_context = _build_discovery_context_from_seeds(
            seed_keywords=seed_keywords,
            seed_category_urls=seed_category_urls,
            asin_pool=pool,
            expand_keywords=expand_keywords,
        )
    if not discovery_context and not pool:
        return {"niches": [], "summary": {"total": 0, "seed_sources": 0}}

    try:
        from amazon_research.clustering import cluster_products
        from amazon_research.ranking import rank_cluster_opportunities
        from amazon_research.niche import score_niches
        from amazon_research.index import build_market_opportunity_index
    except ImportError as e:
        logger.warning("niche_discovery: missing deps: %s", e)
        return {"niches": [], "summary": {"total": 0, "error": str(e)}}

    clusters_out = cluster_products(
        pool if pool else [f"placeholder_{i}" for i in range(len(discovery_context))],
        discovery_context=discovery_context,
        use_db=use_db,
    )
    clusters = clusters_out.get("clusters") or []
    if limit is not None and limit > 0:
        clusters = clusters[:limit]

    if not clusters:
        return {"niches": [], "summary": {"total": 0, "clusters": 0}}

    rank_out = rank_cluster_opportunities(clusters, asin_pool=pool or None, use_db=use_db)
    niche_out = score_niches(clusters, asin_pool=pool or None, use_db=use_db)
    moi_out = build_market_opportunity_index(clusters, asin_pool=pool or None, use_db=use_db)

    scored_by_id = {s["cluster_id"]: s for s in niche_out.get("scored_niches") or []}
    rank_by_id = {r["cluster_id"]: r for r in rank_out.get("ranked_candidates") or []}
    moi_by_id = {m["cluster_id"]: m for m in moi_out.get("index_results") or []}

    niches: List[Dict[str, Any]] = []
    for c in clusters:
        cid = c.get("cluster_id") or ""
        seed_source = _seed_source_from_cluster(c)
        related = _related_from_cluster(c)
        member_asins = c.get("member_asins") or []
        cluster_summary = f"{len(member_asins)} ASINs"
        opp_signals = rank_by_id.get(cid) or {}
        contrib = (moi_by_id.get(cid) or {}).get("contributing_signals") or {}
        opportunity_signals_summary = {
            "opportunity_index": (moi_by_id.get(cid) or {}).get("market_opportunity_index"),
            "demand_score": contrib.get("demand_score"),
            "competition_score": contrib.get("competition_score"),
            "trend_score": contrib.get("trend_score"),
            "niche_score": (scored_by_id.get(cid) or {}).get("niche_score"),
            "ranking_score": opp_signals.get("score"),
        }
        niches.append({
            "niche_id": cid,
            "candidate_id": cid,
            "seed_source": seed_source,
            "related_keywords": related.get("keywords") or [],
            "related_categories": related.get("categories") or [],
            "cluster_id": cid,
            "cluster_summary": cluster_summary,
            "opportunity_signals_summary": opportunity_signals_summary,
        })

    niches.sort(key=lambda n: (-((n.get("opportunity_signals_summary") or {}).get("opportunity_index") or 0), n.get("cluster_id", "")))

    return {
        "niches": niches,
        "summary": {
            "total": len(niches),
            "clusters": len(clusters),
            "seed_sources": len(discovery_context),
        },
    }
