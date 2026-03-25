"""
Step 104: Discovery result storage – persist and read scan outputs for reuse.
Stores source_type (category/keyword/graph/automated), source_id, asins, marketplace, scan_metadata.
Compatible with category/keyword scanner, automated niche discovery, reverse ASIN context, dashboard.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.discovery_storage")

SOURCE_TYPE_CATEGORY = "category"
SOURCE_TYPE_KEYWORD = "keyword"
SOURCE_TYPE_GRAPH = "graph"
SOURCE_TYPE_AUTOMATED = "automated"


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def save_discovery_result(
    source_type: str,
    source_id: str,
    asins: List[str],
    *,
    marketplace: Optional[str] = None,
    scan_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """
    Append one discovery result. source_type: category, keyword, graph, automated.
    source_id: category URL, keyword text, or other identifier. asins: list of ASIN strings.
    Returns inserted id or None on error.
    """
    if not isinstance(asins, list):
        asins = []
    asins = [str(a).strip() for a in asins if a and str(a).strip()]
    st = (source_type or "").strip().lower() or SOURCE_TYPE_KEYWORD
    sid = (source_id or "").strip() or ""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        asins_json = json.dumps(asins)
        meta_json = json.dumps(scan_metadata if isinstance(scan_metadata, dict) else {})
        cur.execute(
            """INSERT INTO discovery_results (source_type, source_id, marketplace, asins, scan_metadata)
               VALUES (%s, %s, %s, %s::jsonb, %s::jsonb) RETURNING id""",
            (st, sid, (marketplace or "").strip() or None, asins_json, meta_json),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
        cur.close()
        conn.commit()
        return rid
    except Exception as e:
        logger.debug("save_discovery_result failed: %s", e)
        return None


def get_discovery_result_latest(
    source_type: str,
    source_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Return the most recent discovery result for the source. Result: id, source_type, source_id,
    marketplace, recorded_at, asins, scan_metadata. None if not found or error.
    """
    st = (source_type or "").strip().lower()
    sid = (source_id or "").strip()
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, source_type, source_id, marketplace, recorded_at, asins, scan_metadata
               FROM discovery_results
               WHERE source_type = %s AND source_id = %s
               ORDER BY recorded_at DESC
               LIMIT 1""",
            (st, sid),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        asins = row[5]
        if isinstance(asins, str):
            try:
                asins = json.loads(asins)
            except Exception:
                asins = []
        meta = row[6]
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        return {
            "id": row[0],
            "source_type": row[1],
            "source_id": row[2],
            "marketplace": row[3],
            "recorded_at": row[4],
            "asins": asins if isinstance(asins, list) else [],
            "scan_metadata": meta if isinstance(meta, dict) else {},
        }
    except Exception as e:
        logger.debug("get_discovery_result_latest failed: %s", e)
        return None


def get_discovery_results(
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    List discovery results, newest first. Optional filter by source_type and/or source_id.
    Each item: id, source_type, source_id, marketplace, recorded_at, asins, scan_metadata.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        conditions = []
        params: List[Any] = []
        if source_type:
            conditions.append("source_type = %s")
            params.append((source_type or "").strip().lower())
        if source_id:
            conditions.append("source_id = %s")
            params.append((source_id or "").strip())
        where = " AND ".join(conditions) if conditions else "TRUE"
        params.append(max(1, limit))
        cur.execute(
            f"""SELECT id, source_type, source_id, marketplace, recorded_at, asins, scan_metadata
                FROM discovery_results
                WHERE {where}
                ORDER BY recorded_at DESC
                LIMIT %s""",
            params,
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            asins = row[5]
            if isinstance(asins, str):
                try:
                    asins = json.loads(asins)
                except Exception:
                    asins = []
            meta = row[6]
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            out.append({
                "id": row[0],
                "source_type": row[1],
                "source_id": row[2],
                "marketplace": row[3],
                "recorded_at": row[4],
                "asins": asins if isinstance(asins, list) else [],
                "scan_metadata": meta if isinstance(meta, dict) else {},
            })
        return out
    except Exception as e:
        logger.debug("get_discovery_results failed: %s", e)
        return []


def get_discovery_context_for_asin(
    asin: str,
    limit: int = 100,
    marketplace: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return discovery_context entries for reverse ASIN: list of { source_type, source_id, asins [, marketplace] }
    for each stored result that contains the given ASIN. Step 109: optional marketplace filter for market-aware context.
    """
    a = (asin or "").strip()
    if not a:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if marketplace:
            cur.execute(
                """SELECT source_type, source_id, asins, marketplace
                   FROM discovery_results
                   WHERE asins @> %s::jsonb AND (marketplace = %s OR marketplace IS NULL)
                   ORDER BY recorded_at DESC
                   LIMIT %s""",
                (json.dumps([a]), (marketplace or "").strip(), max(1, limit)),
            )
        else:
            cur.execute(
                """SELECT source_type, source_id, asins, marketplace
                   FROM discovery_results
                   WHERE asins @> %s::jsonb
                   ORDER BY recorded_at DESC
                   LIMIT %s""",
                (json.dumps([a]), max(1, limit)),
            )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            asins = row[2]
            if isinstance(asins, str):
                try:
                    asins = json.loads(asins)
                except Exception:
                    asins = []
            entry = {
                "source_type": row[0],
                "source_id": row[1],
                "asins": asins if isinstance(asins, list) else [],
            }
            if len(row) >= 4 and row[3] is not None:
                entry["marketplace"] = row[3]
            out.append(entry)
        return out
    except Exception as e:
        logger.debug("get_discovery_context_for_asin failed: %s", e)
        return []
