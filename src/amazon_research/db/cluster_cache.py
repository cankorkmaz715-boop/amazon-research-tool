"""
Step 103: Cluster cache layer – store and retrieve computed clustering outputs.
Stores cluster_id, member_asins, label, rationale/signals; timestamp for freshness.
Compatible with niche explorer, opportunity ranking, board, product deep analyzer.
Supports refresh/invalidation when underlying data changes.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.cluster_cache")

DEFAULT_SCOPE = "default"


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def save_cluster_cache(
    clusters: List[Dict[str, Any]],
    *,
    scope_key: Optional[str] = None,
    summary: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """
    Append a cluster cache snapshot. clusters: list of dicts with cluster_id, member_asins, label, rationale.
    scope_key: optional scope (e.g. workspace id or 'default'). Returns inserted id or None on error.
    """
    scope = (scope_key or "").strip() or DEFAULT_SCOPE
    if not isinstance(clusters, list):
        clusters = []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        clusters_json = json.dumps(clusters)
        summary_json = json.dumps(summary if isinstance(summary, dict) else {})
        cur.execute(
            """INSERT INTO cluster_cache (scope_key, clusters, summary)
               VALUES (%s, %s::jsonb, %s::jsonb) RETURNING id""",
            (scope, clusters_json, summary_json),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
        cur.close()
        conn.commit()
        return rid
    except Exception as e:
        logger.debug("save_cluster_cache failed: %s", e)
        return None


def get_cluster_cache(
    scope_key: Optional[str] = None,
    *,
    limit: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Return the latest cache entry for the scope: clusters, summary, recorded_at.
    If limit > 1 returns the latest single snapshot (one row). Returns None if not found or error.
    """
    scope = (scope_key or "").strip() or DEFAULT_SCOPE
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, scope_key, recorded_at, clusters, summary
               FROM cluster_cache
               WHERE scope_key = %s
               ORDER BY recorded_at DESC
               LIMIT 1""",
            (scope,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        clusters = row[3]
        if isinstance(clusters, str):
            try:
                clusters = json.loads(clusters)
            except Exception:
                clusters = []
        summary = row[4]
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except Exception:
                summary = {}
        return {
            "id": row[0],
            "scope_key": row[1],
            "recorded_at": row[2],
            "clusters": clusters if isinstance(clusters, list) else [],
            "summary": summary if isinstance(summary, dict) else {},
        }
    except Exception as e:
        logger.debug("get_cluster_cache failed: %s", e)
        return None


def get_cluster_cache_freshness(scope_key: Optional[str] = None) -> Optional[Any]:
    """
    Return recorded_at of the latest cache entry for the scope, or None.
    Use for freshness checks and invalidation decisions.
    """
    entry = get_cluster_cache(scope_key=scope_key)
    if not entry:
        return None
    return entry.get("recorded_at")


def invalidate_cluster_cache(scope_key: Optional[str] = None) -> int:
    """
    Delete all cache entries for the scope. Returns number of rows deleted.
    Safe refresh: call after underlying data changes, then save_cluster_cache with new data.
    """
    scope = (scope_key or "").strip() or DEFAULT_SCOPE
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cluster_cache WHERE scope_key = %s", (scope,))
        n = cur.rowcount
        cur.close()
        conn.commit()
        return n
    except Exception as e:
        logger.debug("invalidate_cluster_cache failed: %s", e)
        return 0
