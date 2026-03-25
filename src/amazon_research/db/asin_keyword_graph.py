"""
Step 106: Reverse ASIN keyword graph – graph-like relationship layer between ASINs and keywords.
Stores asin, keyword, source_context, marketplace, timestamp. Usable for reverse ASIN analysis,
advanced keyword expansion, automated niche discovery. Populate from discovery results, keyword scans, expansion.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.asin_keyword_graph")

SOURCE_KEYWORD_SCAN = "keyword_scan"
SOURCE_DISCOVERY_RESULT = "discovery_result"
SOURCE_EXPANSION = "expansion"


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def add_asin_keyword_edge(
    asin: str,
    keyword: str,
    source_context: str = SOURCE_KEYWORD_SCAN,
    marketplace: Optional[str] = None,
) -> Optional[int]:
    """
    Append one ASIN–keyword edge. Returns inserted id or None on error.
    source_context: keyword_scan, discovery_result, expansion, etc.
    """
    a = (asin or "").strip()
    kw = (keyword or "").strip()
    if not a or not kw:
        return None
    ctx = (source_context or SOURCE_KEYWORD_SCAN).strip() or SOURCE_KEYWORD_SCAN
    market = (marketplace or "DE").strip() or "DE"
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO asin_keyword_edges (asin, keyword, source_context, marketplace)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (a, kw, ctx, market),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
        cur.close()
        conn.commit()
        return rid
    except Exception as e:
        logger.debug("add_asin_keyword_edge failed: %s", e)
        return None


def add_asin_keyword_edges_bulk(
    asins: List[str],
    keyword: str,
    source_context: str = SOURCE_KEYWORD_SCAN,
    marketplace: Optional[str] = None,
) -> int:
    """
    Add one edge per (asin, keyword) for the given keyword and asin list. Returns count inserted.
    Use after keyword scan or when persisting discovery result (keyword scan output).
    """
    if not asins or not (keyword or "").strip():
        return 0
    ctx = (source_context or SOURCE_KEYWORD_SCAN).strip() or SOURCE_KEYWORD_SCAN
    market = (marketplace or "DE").strip() or "DE"
    kw = (keyword or "").strip()
    n = 0
    try:
        conn = _get_connection()
        cur = conn.cursor()
        for asin in asins:
            a = (str(asin).strip() if asin else "").strip()
            if not a:
                continue
            cur.execute(
                """INSERT INTO asin_keyword_edges (asin, keyword, source_context, marketplace)
                   VALUES (%s, %s, %s, %s)""",
                (a, kw, ctx, market),
            )
            n += cur.rowcount
        cur.close()
        conn.commit()
        return n
    except Exception as e:
        logger.debug("add_asin_keyword_edges_bulk failed: %s", e)
        return 0


def get_keywords_for_asin(
    asin: str,
    limit: int = 100,
    marketplace: Optional[str] = None,
    source_context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return keywords linked to this ASIN (reverse lookup). Each item: keyword, source_context, recorded_at.
    Optional filter by marketplace and source_context.
    """
    a = (asin or "").strip()
    if not a:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        conditions = ["asin = %s"]
        params: List[Any] = [a]
        if marketplace:
            conditions.append("marketplace = %s")
            params.append((marketplace or "").strip())
        if source_context:
            conditions.append("source_context = %s")
            params.append((source_context or "").strip())
        params.append(max(1, limit))
        cur.execute(
            f"""SELECT keyword, source_context, recorded_at
                FROM asin_keyword_edges
                WHERE {' AND '.join(conditions)}
                ORDER BY recorded_at DESC
                LIMIT %s""",
            params,
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {"keyword": row[0], "source_context": row[1], "recorded_at": row[2]}
            for row in rows
        ]
    except Exception as e:
        logger.debug("get_keywords_for_asin failed: %s", e)
        return []


def get_asins_for_keyword(
    keyword: str,
    limit: int = 100,
    marketplace: Optional[str] = None,
    source_context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return ASINs linked to this keyword. Each item: asin, source_context, recorded_at.
    Optional filter by marketplace and source_context.
    """
    kw = (keyword or "").strip()
    if not kw:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        conditions = ["keyword = %s"]
        params: List[Any] = [kw]
        if marketplace:
            conditions.append("marketplace = %s")
            params.append((marketplace or "").strip())
        if source_context:
            conditions.append("source_context = %s")
            params.append((source_context or "").strip())
        params.append(max(1, limit))
        cur.execute(
            f"""SELECT asin, source_context, recorded_at
                FROM asin_keyword_edges
                WHERE {' AND '.join(conditions)}
                ORDER BY recorded_at DESC
                LIMIT %s""",
            params,
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {"asin": row[0], "source_context": row[1], "recorded_at": row[2]}
            for row in rows
        ]
    except Exception as e:
        logger.debug("get_asins_for_keyword failed: %s", e)
        return []


def sync_edges_from_discovery_result(
    source_type: str,
    source_id: str,
    asins: List[str],
    marketplace: Optional[str] = None,
    source_context: str = SOURCE_DISCOVERY_RESULT,
) -> int:
    """
    Write ASIN–keyword edges for a single discovery result (e.g. one keyword scan).
    When source_type is 'keyword', source_id is the keyword. Returns count of edges added.
    """
    if (source_type or "").strip().lower() != "keyword":
        return 0
    keyword = (source_id or "").strip()
    if not keyword or not asins:
        return 0
    return add_asin_keyword_edges_bulk(
        asins,
        keyword,
        source_context=source_context,
        marketplace=marketplace,
    )
