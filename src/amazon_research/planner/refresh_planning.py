"""
Distributed refresh planning v1. Step 67 – candidate selection, priority ordering, batch partitioning.
Output is queue- and worker-friendly (batches can be enqueued as refresh jobs with asin_list payload).
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from amazon_research.db.connection import get_connection

logger = get_logger("planner.refresh_planning")

ORDERING_OLDEST_FIRST = "oldest_first"


def get_refresh_candidates(
    workspace_id: Optional[int] = None,
    limit: int = 100,
    ordering: str = ORDERING_OLDEST_FIRST,
) -> List[Dict[str, Any]]:
    """
    Return ASINs that are eligible for refresh: not in skip backoff, ordered by priority.
    Each item: {"asin_id": int, "asin": str}.
    """
    conn = get_connection()
    cur = conn.cursor()
    if ordering == ORDERING_OLDEST_FIRST:
        cur.execute(
            """
            SELECT a.id, a.asin
            FROM asins a
            LEFT JOIN product_metrics pm ON pm.asin_id = a.id
            LEFT JOIN asin_attempt_state aas ON aas.asin_id = a.id
            WHERE (aas.skip_until IS NULL OR aas.skip_until <= CURRENT_TIMESTAMP)
            AND (a.workspace_id = %s OR (%s IS NULL AND a.workspace_id IS NULL))
            ORDER BY pm.updated_at ASC NULLS FIRST, a.id ASC
            LIMIT %s
            """,
            (workspace_id, workspace_id, limit),
        )
    else:
        cur.execute(
            """
            SELECT a.id, a.asin
            FROM asins a
            LEFT JOIN asin_attempt_state aas ON aas.asin_id = a.id
            WHERE (aas.skip_until IS NULL OR aas.skip_until <= CURRENT_TIMESTAMP)
            AND (a.workspace_id = %s OR (%s IS NULL AND a.workspace_id IS NULL))
            ORDER BY a.id ASC
            LIMIT %s
            """,
            (workspace_id, workspace_id, limit),
        )
    rows = cur.fetchall()
    cur.close()
    return [{"asin_id": r[0], "asin": r[1]} for r in rows]


def build_refresh_plan(
    workspace_id: Optional[int] = None,
    candidate_limit: int = 100,
    batch_size: int = 5,
    ordering: str = ORDERING_OLDEST_FIRST,
) -> Dict[str, Any]:
    """
    Build a refresh plan: candidates plus batches (each batch is a list of ASIN strings).
    Queue-friendly: each batch can be enqueued as a refresh job with payload {"asin_list": batch}.
    """
    candidates = get_refresh_candidates(
        workspace_id=workspace_id,
        limit=candidate_limit,
        ordering=ordering,
    )
    asin_strings = [c["asin"] for c in candidates]
    batches: List[List[str]] = []
    for i in range(0, len(asin_strings), batch_size):
        batches.append(asin_strings[i : i + batch_size])
    return {
        "candidates": candidates,
        "candidates_count": len(candidates),
        "batches": batches,
        "batch_count": len(batches),
        "ordering": ordering,
    }
