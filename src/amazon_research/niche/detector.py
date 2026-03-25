"""
Niche detector foundation v1. Step 79 – group/flag ASIN sets by context and co-occurrence.
Lightweight, explainable; outputs clean niche candidates for later scoring and clustering.
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("niche.detector")


def detect_niches(
    asin_pool: List[str],
    discovery_context: Optional[List[Dict[str, Any]]] = None,
    workspace_id: Optional[int] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Build niche candidates from an ASIN pool using simple signals.
    Signals: shared category context, shared keyword context, co-occurrence (graph), metadata overlap.
    Returns { candidates, summary } with explainable structure.
    """
    pool = list({str(a).strip() for a in asin_pool if (a and str(a).strip())})
    candidates: List[Dict[str, Any]] = []
    by_signal: Dict[str, int] = defaultdict(int)

    # --- 1. Discovery context: category and keyword groups ---
    if discovery_context:
        for ctx in discovery_context:
            source_type = (ctx.get("source_type") or "").strip().lower()
            source_id = ctx.get("source_id") or ""
            asins = [str(a).strip() for a in (ctx.get("asins") or []) if a]
            asins = [a for a in asins if a in pool or not pool]  # restrict to pool if pool non-empty
            if not asins and pool:
                continue
            if not asins:
                asins = list(pool)
            if source_type == "category":
                candidates.append({
                    "asin_set": list(asins),
                    "signals": {
                        "category_context": {"source_type": "category", "source_id": source_id},
                        "keyword_context": None,
                        "co_occurrence": None,
                        "metadata_overlap": None,
                    },
                    "explanation": f"{len(asins)} ASINs from category context {source_id!r}",
                })
                by_signal["category_context"] += 1
            elif source_type == "keyword":
                candidates.append({
                    "asin_set": list(asins),
                    "signals": {
                        "category_context": None,
                        "keyword_context": {"source_type": "keyword", "source_id": source_id},
                        "co_occurrence": None,
                        "metadata_overlap": None,
                    },
                    "explanation": f"{len(asins)} ASINs from keyword context {source_id!r}",
                })
                by_signal["keyword_context"] += 1

    if not use_db:
        return _result(candidates, by_signal, pool)
    try:
        from amazon_research.db import get_asins_metadata, get_relationships_for_asin_ids
    except ImportError:
        logger.warning("niche detector: DB not available, skipping co-occurrence and metadata")
        return _result(candidates, by_signal, pool)

    meta = get_asins_metadata(pool)
    pool_id_to_asin = {r["id"]: r["asin"] for r in meta}
    pool_asin_to_id = {r["asin"]: r["id"] for r in meta}
    pool_ids = list(pool_id_to_asin.keys())

    # --- 2. Co-occurrence: ASINs that share a common neighbor in the graph ---
    if pool_ids:
        edges = get_relationships_for_asin_ids(pool_ids, limit=5000)
        neighbor_to_pool_ids: Dict[int, List[int]] = defaultdict(list)
        for e in edges:
            f, t = e["from_asin_id"], e["to_asin_id"]
            if f in pool_ids and t not in pool_ids:
                neighbor_to_pool_ids[t].append(f)
            elif t in pool_ids and f not in pool_ids:
                neighbor_to_pool_ids[f].append(t)
        for neighbor_id, ids in neighbor_to_pool_ids.items():
            if len(ids) < 2:
                continue
            asin_set = [pool_id_to_asin[i] for i in ids if i in pool_id_to_asin]
            if len(asin_set) < 2:
                continue
            candidates.append({
                "asin_set": asin_set,
                "signals": {
                    "category_context": None,
                    "keyword_context": None,
                    "co_occurrence": {
                        "shared_neighbor_asin_id": neighbor_id,
                        "relationship_count": len(ids),
                    },
                    "metadata_overlap": None,
                },
                "explanation": f"{len(asin_set)} ASINs co-occur (share neighbor asin_id={neighbor_id})",
            })
            by_signal["co_occurrence"] += 1

    # --- 3. Metadata overlap: group by (category, brand) from asins table ---
    if meta:
        key_to_asins: Dict[tuple, List[str]] = defaultdict(list)
        for r in meta:
            cat = (r.get("category") or "").strip() or None
            brand = (r.get("brand") or "").strip() or None
            key = (cat, brand)
            key_to_asins[key].append(r["asin"])
        for key, asin_list in key_to_asins.items():
            if not asin_list:
                continue
            cat, brand = key
            candidates.append({
                "asin_set": asin_list,
                "signals": {
                    "category_context": None,
                    "keyword_context": None,
                    "co_occurrence": None,
                    "metadata_overlap": {"category": cat, "brand": brand},
                },
                "explanation": f"{len(asin_list)} ASINs with category={cat!r}, brand={brand!r}",
            })
            by_signal["metadata_overlap"] += 1

    return _result(candidates, by_signal, pool)


def _result(
    candidates: List[Dict[str, Any]],
    by_signal: Dict[str, int],
    pool: List[str],
) -> Dict[str, Any]:
    summary = {
        "total_candidates": len(candidates),
        "pool_size": len(pool),
        "by_signal": dict(by_signal),
    }
    return {
        "candidates": candidates,
        "summary": summary,
    }
