"""
Controlled graph expansion v1 – discover candidate ASINs from the relationship graph.
Step 40: Small limited set of nodes, strict caps, aggressive dedupe, persist via current layer.
No concurrency; scheduler-friendly.
"""
from typing import Any, Dict, List, Set

from amazon_research.logging_config import get_logger
from amazon_research.config import get_config
from amazon_research.db import (
    get_connection,
    get_asin_by_id,
    list_relationships,
    upsert_asin,
)

logger = get_logger("bots.graph_expansion")


def run_graph_expansion() -> Dict[str, Any]:
    """
    Run one controlled expansion pass: read from graph, collect candidate ASINs, persist.
    Respects config caps: max_expansion_nodes, max_expansion_candidates, max_expansion_persist.
    Returns dict: nodes_visited, candidates_collected (raw from edges), deduped (unique ASINs), persisted.
    """
    cfg = get_config()
    max_nodes = max(1, min(50, cfg.max_expansion_nodes))
    max_candidates = max(1, min(200, cfg.max_expansion_candidates))
    max_persist = max(0, min(100, cfg.max_expansion_persist))

    nodes_visited = 0
    raw_to_ids: List[int] = []
    seen_ids: Set[int] = set()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT from_asin_id FROM asin_relationships
        ORDER BY from_asin_id
        LIMIT %s
        """,
        (max_nodes,),
    )
    seed_ids = [r[0] for r in cur.fetchall()]
    cur.close()

    for from_id in seed_ids:
        if nodes_visited >= max_nodes:
            break
        if len(raw_to_ids) >= max_candidates:
            break
        edges = list_relationships(asin_id=from_id, direction="out", limit=max_candidates - len(raw_to_ids))
        for e in edges:
            to_id = e.get("to_asin_id")
            if to_id is not None and to_id not in seen_ids:
                seen_ids.add(to_id)
                raw_to_ids.append(to_id)
                if len(raw_to_ids) >= max_candidates:
                    break
        nodes_visited += 1

    # Resolve to_asin_id -> ASIN string; dedupe by ASIN
    candidate_asins: List[str] = []
    seen_asin: Set[str] = set()
    for to_id in raw_to_ids:
        asin = get_asin_by_id(to_id)
        if asin and asin.strip() and asin.upper() not in seen_asin:
            seen_asin.add(asin.upper())
            candidate_asins.append(asin)

    deduped_count = len(candidate_asins)
    persisted = 0
    for asin in candidate_asins[:max_persist]:
        try:
            upsert_asin(asin)
            persisted += 1
        except Exception as e:
            logger.warning("graph_expansion: upsert_asin failed for %s: %s", asin[:20], e)

    result = {
        "nodes_visited": nodes_visited,
        "candidates_collected": len(raw_to_ids),
        "new_asins": deduped_count,
        "deduped": deduped_count,
        "persisted": persisted,
    }
    try:
        from amazon_research.monitoring import record_cost_hint
        record_cost_hint("graph_expansion", "nodes_visited", nodes_visited)
    except Exception:
        pass
    logger.info("graph_expansion run finished", extra=result)
    return result
