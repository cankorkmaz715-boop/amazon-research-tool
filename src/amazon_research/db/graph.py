"""
ASIN relationship graph – store and query ASIN-to-ASIN edges with source type.
Step 38: Simple DB-backed graph. Step 39: persist related/sponsored discovery candidates.
Source types: e.g. 'related', 'sponsored', 'seed' – application-defined.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection
from .persistence import get_asin_id, upsert_asin

logger = get_logger("db.graph")


def persist_related_sponsored_candidates(
    from_asin_id: int,
    candidates: List[Dict[str, Any]],
) -> int:
    """
    Persist related/sponsored discovery candidates into the graph.
    candidates: list of {"asin": str, "source_type": "related"|"sponsored"}.
    Upserts each ASIN, then adds edge (from_asin_id -> to_asin_id, source_type).
    Returns count of new relationships stored (duplicates skipped).
    """
    count = 0
    for c in candidates:
        asin = (c.get("asin") or "").strip()
        source_type = (c.get("source_type") or "related").strip() or "related"
        if not asin or source_type not in ("related", "sponsored"):
            continue
        try:
            upsert_asin(asin)
            to_id = get_asin_id(asin)
            if not to_id:
                continue
            rid = add_asin_relationship(from_asin_id, to_id, source_type)
            if rid is not None:
                count += 1
        except Exception as e:
            logger.warning("persist_related_sponsored_candidates: skip %s: %s", asin, e)
    return count


def add_asin_relationship(
    from_asin_id: int,
    to_asin_id: int,
    source_type: str = "related",
) -> Optional[int]:
    """
    Store an edge from_asin_id -> to_asin_id with source_type.
    Returns relationship id if inserted, None if duplicate (same from, to, source_type).
    """
    if from_asin_id == to_asin_id:
        return None
    source_type = (source_type or "related").strip() or "related"
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO asin_relationships (from_asin_id, to_asin_id, source_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (from_asin_id, to_asin_id, source_type) DO NOTHING
            RETURNING id
            """,
            (from_asin_id, to_asin_id, source_type),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
    finally:
        cur.close()
    conn.commit()
    return rid


def list_relationships(
    asin_id: Optional[int] = None,
    direction: str = "out",
    source_type: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    List edges. If asin_id given, filter by from (out), to (in), or both.
    direction: 'out' | 'in' | 'both'. source_type: filter by type.
    Returns list of dicts: id, from_asin_id, to_asin_id, source_type, created_at.
    """
    conn = get_connection()
    cur = conn.cursor()
    conditions = []
    params: List[Any] = []
    if asin_id is not None:
        if direction == "out":
            conditions.append("from_asin_id = %s")
            params.append(asin_id)
        elif direction == "in":
            conditions.append("to_asin_id = %s")
            params.append(asin_id)
        else:
            conditions.append("(from_asin_id = %s OR to_asin_id = %s)")
            params.extend([asin_id, asin_id])
    if source_type is not None:
        conditions.append("source_type = %s")
        params.append(source_type)
    where = " AND ".join(conditions) if conditions else "TRUE"
    sql = f"SELECT id, from_asin_id, to_asin_id, source_type, created_at FROM asin_relationships WHERE {where} ORDER BY id"
    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "id": r[0],
            "from_asin_id": r[1],
            "to_asin_id": r[2],
            "source_type": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


def get_relationships_for_asin_ids(
    asin_ids: List[int],
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Return all edges where either from_asin_id or to_asin_id is in asin_ids.
    Step 79: Niche detector – co-occurrence from graph. Returns same shape as list_relationships.
    """
    if not asin_ids:
        return []
    conn = get_connection()
    cur = conn.cursor()
    params: List[Any] = [list(asin_ids), list(asin_ids)]
    sql = (
        "SELECT id, from_asin_id, to_asin_id, source_type, created_at "
        "FROM asin_relationships WHERE from_asin_id = ANY(%s) OR to_asin_id = ANY(%s) ORDER BY id"
    )
    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "id": r[0],
            "from_asin_id": r[1],
            "to_asin_id": r[2],
            "source_type": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]
