"""
Step 197: Workspace portfolio items – track opportunities, ASINs, niches, categories, markets, keywords per workspace.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.workspace_portfolio")

ITEM_TYPES = frozenset({"opportunity", "asin", "niche", "category", "market", "keyword"})
STATUS_ACTIVE = "active"
STATUS_ARCHIVED = "archived"
STATUS_VALUES = frozenset({STATUS_ACTIVE, STATUS_ARCHIVED})


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_metadata(val: Any) -> Dict[str, Any]:
    if val is None:
        return {}
    if isinstance(val, dict):
        return dict(val)
    if isinstance(val, str) and val.strip():
        try:
            return json.loads(val)
        except Exception:
            return {}
    return {}


def add_workspace_portfolio_item(
    workspace_id: int,
    item_type: str,
    item_key: str,
    item_label: Optional[str] = None,
    source_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Add a portfolio item. Deduplication: (workspace_id, item_type, item_key).
    Returns { "id": int, "created": bool } or { "id": int, "created": False } if already existed.
    Logs add start, success, deduplicated.
    """
    ttype = (item_type or "").strip().lower()
    if ttype not in ITEM_TYPES:
        ttype = "opportunity"
    key = (item_key or "").strip()
    if not key:
        return {"id": None, "created": False}
    label = (item_label or "").strip() or None
    source = (source_type or "").strip() or None
    meta = _safe_metadata(metadata)
    meta_json = json.dumps(meta) if meta else "{}"
    logger.info("workspace_portfolio add start workspace_id=%s item_type=%s item_key=%s", workspace_id, ttype, key)
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id FROM workspace_portfolio_items
               WHERE workspace_id = %s AND item_type = %s AND item_key = %s""",
            (workspace_id, ttype, key),
        )
        existing = cur.fetchone()
        if existing:
            rid = existing[0]
            cur.execute(
                """UPDATE workspace_portfolio_items SET
                   item_label = COALESCE(NULLIF(%s, ''), item_label),
                   source_type = COALESCE(NULLIF(%s, ''), source_type),
                   metadata_json = COALESCE(NULLIF(%s::text, '{}'), metadata_json),
                   updated_at = %s
                   WHERE id = %s""",
                (label or "", source or "", meta_json, _now_utc(), rid),
            )
            cur.close()
            conn.commit()
            logger.info("workspace_portfolio add deduplicated workspace_id=%s id=%s", workspace_id, rid)
            return {"id": rid, "created": False}
        cur.execute(
            """INSERT INTO workspace_portfolio_items
               (workspace_id, item_type, item_key, item_label, source_type, metadata_json, status, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
               RETURNING id""",
            (workspace_id, ttype, key, label, source, meta_json, STATUS_ACTIVE, _now_utc(), _now_utc()),
        )
        row = cur.fetchone()
        cur.close()
        conn.commit()
        if row:
            rid = row[0]
            logger.info("workspace_portfolio add success workspace_id=%s id=%s", workspace_id, rid)
            return {"id": rid, "created": True}
    except Exception as e:
        logger.warning("workspace_portfolio add failure workspace_id=%s: %s", workspace_id, e)
    return {"id": None, "created": False}


def list_workspace_portfolio_items(
    workspace_id: Optional[int],
    item_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """List portfolio items for workspace. Optional filters: item_type, status. Returns [] on error."""
    if workspace_id is None:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        conditions = ["workspace_id = %s"]
        params: List[Any] = [workspace_id]
        if item_type and (item_type or "").strip().lower() in ITEM_TYPES:
            conditions.append("item_type = %s")
            params.append((item_type or "").strip().lower())
        if status and (status or "").strip().lower() in STATUS_VALUES:
            conditions.append("status = %s")
            params.append((status or "").strip().lower())
        params.append(max(1, limit))
        cur.execute(
            f"""SELECT id, workspace_id, item_type, item_key, item_label, source_type, metadata_json, status, created_at, updated_at
                FROM workspace_portfolio_items
                WHERE {' AND '.join(conditions)}
                ORDER BY updated_at DESC
                LIMIT %s""",
            params,
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for r in rows:
            meta = r[6]
            if isinstance(meta, str) and meta:
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            if not isinstance(meta, dict):
                meta = {}
            out.append({
                "id": r[0],
                "workspace_id": r[1],
                "item_type": r[2],
                "item_key": r[3],
                "item_label": r[4],
                "source_type": r[5],
                "metadata_json": meta,
                "status": r[7],
                "created_at": r[8],
                "updated_at": r[9],
            })
        return out
    except Exception as e:
        logger.warning("list_workspace_portfolio_items failed workspace_id=%s: %s", workspace_id, e)
        return []


def get_workspace_portfolio_item_by_key(
    workspace_id: int,
    item_type: str,
    item_key: str,
) -> Optional[Dict[str, Any]]:
    """Return one portfolio item by (workspace_id, item_type, item_key), or None."""
    if not (workspace_id and item_key):
        return None
    ttype = (item_type or "opportunity").strip().lower()
    if ttype not in ITEM_TYPES:
        ttype = "opportunity"
    key = (item_key or "").strip()
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, item_type, item_key, item_label, source_type, metadata_json, status, created_at, updated_at
               FROM workspace_portfolio_items
               WHERE workspace_id = %s AND item_type = %s AND item_key = %s""",
            (workspace_id, ttype, key),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        meta = row[6]
        if isinstance(meta, str) and meta:
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        return {
            "id": row[0],
            "workspace_id": row[1],
            "item_type": row[2],
            "item_key": row[3],
            "item_label": row[4],
            "source_type": row[5],
            "metadata_json": meta if isinstance(meta, dict) else {},
            "status": row[7],
            "created_at": row[8],
            "updated_at": row[9],
        }
    except Exception as e:
        logger.warning("get_workspace_portfolio_item_by_key failed: %s", e)
        return None


def archive_workspace_portfolio_item(workspace_id: int, item_id: int) -> bool:
    """Set status to archived for the item. Returns True if updated, False otherwise."""
    if workspace_id is None or item_id is None:
        return False
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """UPDATE workspace_portfolio_items SET status = %s, updated_at = %s
               WHERE id = %s AND workspace_id = %s""",
            (STATUS_ARCHIVED, _now_utc(), item_id, workspace_id),
        )
        n = cur.rowcount
        cur.close()
        conn.commit()
        if n:
            logger.info("workspace_portfolio archive success workspace_id=%s item_id=%s", workspace_id, item_id)
        return n > 0
    except Exception as e:
        logger.warning("workspace_portfolio archive failure workspace_id=%s item_id=%s: %s", workspace_id, item_id, e)
        return False


def get_workspace_portfolio_summary(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Return counts by item_type and by status. Stable shape; empty counts when no items or on error."""
    out: Dict[str, Any] = {"workspace_id": workspace_id, "total": 0, "by_type": {}, "by_status": {"active": 0, "archived": 0}}
    if workspace_id is None:
        return out
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT item_type, status, COUNT(*) FROM workspace_portfolio_items
               WHERE workspace_id = %s GROUP BY item_type, status""",
            (workspace_id,),
        )
        rows = cur.fetchall()
        cur.close()
        total = 0
        for r in rows:
            t, s, c = r[0], r[1], int(r[2])
            total += c
            out["by_type"][t] = out["by_type"].get(t, 0) + c
            out["by_status"][s] = out["by_status"].get(s, 0) + c
        out["total"] = total
        logger.info("workspace_portfolio summary read workspace_id=%s total=%s", workspace_id, total)
    except Exception as e:
        logger.warning("workspace_portfolio summary failed workspace_id=%s: %s", workspace_id, e)
    return out
