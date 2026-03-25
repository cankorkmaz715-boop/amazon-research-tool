"""
Product clustering foundation v1. Step 81 – rule-based clusters from ASIN pools and metadata.
Reuses niche detector; adds title/token similarity and brand-only grouping.
Lightweight, explainable; outputs stable cluster id, members, label, rationale.
"""
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from amazon_research.logging_config import get_logger

logger = get_logger("clustering.product_clustering")


def _tokenize(text: Optional[str]) -> Set[str]:
    """Lowercase, alphanumeric tokens."""
    if not text or not str(text).strip():
        return set()
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _union_find_components(pairs: List[tuple]) -> List[Set[str]]:
    """Given list of (a, b) pairs to link, return list of connected components (sets of elements)."""
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        pa, pb = find(a), find(b)
        if pa != pb:
            parent[pa] = pb

    for a, b in pairs:
        union(a, b)
    components: Dict[str, Set[str]] = defaultdict(set)
    for x in parent:
        root = find(x)
        components[root].add(x)
    return list(components.values())


def _clusters_from_niche_candidates(
    niche_result: Dict[str, Any],
    pool: List[str],
) -> List[Dict[str, Any]]:
    """Convert niche detector candidates to cluster format with cluster_id, member_asins, label, rationale."""
    clusters: List[Dict[str, Any]] = []
    for i, cand in enumerate(niche_result.get("candidates") or []):
        asin_set = cand.get("asin_set") or []
        if not asin_set:
            continue
        signals = cand.get("signals") or {}
        explanation = cand.get("explanation") or ""
        cluster_id = f"niche_{i}"
        label = explanation[:80] + ("..." if len(explanation) > 80 else "")
        clusters.append({
            "cluster_id": cluster_id,
            "member_asins": list(asin_set),
            "label": label,
            "rationale": {"signals": signals, "source": "niche"},
        })
    return clusters


def _clusters_from_title_tokens(
    meta: List[Dict[str, Any]],
    pool: List[str],
    min_similarity: float = 0.2,
    min_cluster_size: int = 2,
) -> List[Dict[str, Any]]:
    """Group ASINs by title token similarity (Jaccard). Returns clusters with rationale."""
    asin_to_tokens: Dict[str, Set[str]] = {}
    for r in meta:
        asin = r.get("asin")
        title = r.get("title")
        if asin and (asin in pool or not pool):
            asin_to_tokens[asin] = _tokenize(title)
    asins = [a for a in asin_to_tokens if asin_to_tokens[a]]
    if len(asins) < min_cluster_size:
        return []
    pairs: List[tuple] = []
    for i, a in enumerate(asins):
        for b in asins[i + 1 :]:
            if _jaccard(asin_to_tokens[a], asin_to_tokens[b]) >= min_similarity:
                pairs.append((a, b))
    components = _union_find_components(pairs)
    clusters = []
    for idx, comp in enumerate(components):
        if len(comp) < min_cluster_size:
            continue
        member_asins = sorted(comp)
        tokens = set()
        for asin in member_asins:
            tokens |= asin_to_tokens.get(asin, set())
        label = f"Title tokens ({len(member_asins)} ASINs): {', '.join(sorted(tokens)[:8])}{'...' if len(tokens) > 8 else ''}"
        clusters.append({
            "cluster_id": f"title_{idx}",
            "member_asins": member_asins,
            "label": label,
            "rationale": {
                "signals": {"title_token_similarity": {"min_similarity": min_similarity, "token_count": len(tokens)}},
                "source": "title_tokens",
            },
        })
    return clusters


def _clusters_from_brand(
    meta: List[Dict[str, Any]],
    pool: List[str],
    min_cluster_size: int = 2,
) -> List[Dict[str, Any]]:
    """Group ASINs by brand. One cluster per brand with >= min_cluster_size members."""
    brand_to_asins: Dict[str, List[str]] = defaultdict(list)
    for r in meta:
        asin = r.get("asin")
        brand = (r.get("brand") or "").strip() or None
        if not brand or not asin:
            continue
        if asin in pool or not pool:
            brand_to_asins[brand].append(asin)
    clusters = []
    for idx, (brand, asins) in enumerate(brand_to_asins.items()):
        if len(asins) < min_cluster_size:
            continue
        clusters.append({
            "cluster_id": f"brand_{idx}",
            "member_asins": list(asins),
            "label": f"Brand: {brand} ({len(asins)} ASINs)",
            "rationale": {"signals": {"brand_overlap": {"brand": brand}}, "source": "brand"},
        })
    return clusters


def cluster_products(
    asin_pool: List[str],
    discovery_context: Optional[List[Dict[str, Any]]] = None,
    workspace_id: Optional[int] = None,
    use_db: bool = True,
    *,
    title_min_similarity: float = 0.2,
    title_min_cluster_size: int = 2,
    brand_min_cluster_size: int = 2,
) -> Dict[str, Any]:
    """
    Build product clusters from ASIN pool using simple, explainable signals.
    Signals: shared category/keyword context (via niche), title token similarity, brand overlap,
    co-occurrence/graph (via niche), metadata overlap (via niche).
    Returns { clusters, summary } with cluster_id, member_asins, label, rationale per cluster.
    """
    pool = list({str(a).strip() for a in asin_pool if (a and str(a).strip())})
    all_clusters: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    # --- 1. Niche-based clusters (category, keyword, co-occurrence, metadata_overlap) ---
    try:
        from amazon_research.niche import detect_niches
    except ImportError:
        logger.warning("product_clustering: niche detector not available")
    else:
        niche_result = detect_niches(
            pool,
            discovery_context=discovery_context,
            workspace_id=workspace_id,
            use_db=use_db,
        )
        niche_clusters = _clusters_from_niche_candidates(niche_result, pool)
        for c in niche_clusters:
            cid = c["cluster_id"]
            while cid in seen_ids:
                cid = cid + "_"
            seen_ids.add(cid)
            c["cluster_id"] = cid
            all_clusters.append(c)

    # --- 2. Title/token similarity and brand overlap (need metadata with title) ---
    meta: List[Dict[str, Any]] = []
    if use_db and pool:
        try:
            from amazon_research.db import get_asins_metadata
            meta = get_asins_metadata(pool)
        except Exception as e:
            logger.debug("product_clustering: get_asins_metadata failed: %s", e)

    if meta:
        title_clusters = _clusters_from_title_tokens(
            meta,
            pool,
            min_similarity=title_min_similarity,
            min_cluster_size=title_min_cluster_size,
        )
        for c in title_clusters:
            cid = c["cluster_id"]
            while cid in seen_ids:
                cid = cid + "_"
            seen_ids.add(cid)
            c["cluster_id"] = cid
            all_clusters.append(c)

        brand_clusters = _clusters_from_brand(meta, pool, min_cluster_size=brand_min_cluster_size)
        for c in brand_clusters:
            cid = c["cluster_id"]
            while cid in seen_ids:
                cid = cid + "_"
            seen_ids.add(cid)
            c["cluster_id"] = cid
            all_clusters.append(c)

    summary = {
        "cluster_count": len(all_clusters),
        "pool_size": len(pool),
    }
    return {
        "clusters": all_clusters,
        "summary": summary,
    }
