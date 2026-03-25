"""
Step 131: Portfolio watches – register watch targets (ASIN, keyword, niche, cluster) for monitoring.
Stores last_snapshot for change detection. Used by portfolio watch engine.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.portfolio_watches")

TARGET_ASIN = "asin"
TARGET_KEYWORD = "keyword"
TARGET_NICHE = "niche"
TARGET_CLUSTER = "cluster"


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def add_watch(
    workspace_id: int,
    target_type: str,
    target_ref: str,
) -> Optional[int]:
    """
    Register a watch for the given entity. target_type: asin | keyword | niche | cluster.
    target_ref: ASIN string, keyword text, or niche/cluster id. Returns watch id or None.
    """
    ttype = (target_type or "").strip().lower() or TARGET_CLUSTER
    ref = (target_ref or "").strip()
    if not ref:
        return None
    if ttype not in (TARGET_ASIN, TARGET_KEYWORD, TARGET_NICHE, TARGET_CLUSTER):
        ttype = TARGET_CLUSTER
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO portfolio_watches (workspace_id, target_type, target_ref, updated_at)
               VALUES (%s, %s, %s, NOW())
               ON CONFLICT (workspace_id, target_type, target_ref) DO UPDATE SET updated_at = NOW()
               RETURNING id""",
            (workspace_id, ttype, ref),
        )
        row = cur.fetchone()
        wid = row[0] if row else None
        cur.close()
        conn.commit()
        return wid
    except Exception as e:
        logger.debug("add_watch failed: %s", e)
        return None


def remove_watch(watch_id: int, workspace_id: Optional[int] = None) -> bool:
    """Remove a watch by id. If workspace_id provided, only delete when watch belongs to that workspace."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if workspace_id is not None:
            cur.execute("DELETE FROM portfolio_watches WHERE id = %s AND workspace_id = %s", (watch_id, workspace_id))
        else:
            cur.execute("DELETE FROM portfolio_watches WHERE id = %s", (watch_id,))
        n = cur.rowcount
        cur.close()
        conn.commit()
        return n > 0
    except Exception as e:
        logger.debug("remove_watch failed: %s", e)
        return False


def get_watch(watch_id: int, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Return one watch row: id, workspace_id, target_type, target_ref, last_snapshot, created_at, updated_at."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, workspace_id, target_type, target_ref, last_snapshot, created_at, updated_at FROM portfolio_watches WHERE id = %s",
            (watch_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        if workspace_id is not None and row[1] != workspace_id:
            return None
        snap = row[4]
        if isinstance(snap, str):
            try:
                snap = json.loads(snap)
            except Exception:
                snap = {}
        return {
            "id": row[0],
            "workspace_id": row[1],
            "target_type": row[2],
            "target_ref": row[3],
            "last_snapshot": snap if isinstance(snap, dict) else {},
            "created_at": row[5],
            "updated_at": row[6],
        }
    except Exception as e:
        logger.debug("get_watch failed: %s", e)
        return None


def list_watches(
    workspace_id: int,
    target_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List watches for the workspace, optionally filtered by target_type."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if target_type:
            ttype = (target_type or "").strip().lower()
            cur.execute(
                """SELECT id, workspace_id, target_type, target_ref, last_snapshot, created_at, updated_at
                   FROM portfolio_watches WHERE workspace_id = %s AND target_type = %s ORDER BY updated_at DESC LIMIT %s""",
                (workspace_id, ttype, max(1, limit)),
            )
        else:
            cur.execute(
                """SELECT id, workspace_id, target_type, target_ref, last_snapshot, created_at, updated_at
                   FROM portfolio_watches WHERE workspace_id = %s ORDER BY updated_at DESC LIMIT %s""",
                (workspace_id, max(1, limit)),
            )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            snap = row[4]
            if isinstance(snap, str):
                try:
                    snap = json.loads(snap)
                except Exception:
                    snap = {}
            out.append({
                "id": row[0],
                "workspace_id": row[1],
                "target_type": row[2],
                "target_ref": row[3],
                "last_snapshot": snap if isinstance(snap, dict) else {},
                "created_at": row[5],
                "updated_at": row[6],
            })
        return out
    except Exception as e:
        logger.debug("list_watches failed: %s", e)
        return []


def update_watch_snapshot(watch_id: int, snapshot: Dict[str, Any], workspace_id: Optional[int] = None) -> bool:
    """Store last_snapshot for the watch (used after change detection). Returns True if updated."""
    if not isinstance(snapshot, dict):
        return False
    try:
        conn = _get_connection()
        cur = conn.cursor()
        snap_json = json.dumps(snapshot)
        if workspace_id is not None:
            cur.execute(
                "UPDATE portfolio_watches SET last_snapshot = %s::jsonb, updated_at = NOW() WHERE id = %s AND workspace_id = %s",
                (snap_json, watch_id, workspace_id),
            )
        else:
            cur.execute(
                "UPDATE portfolio_watches SET last_snapshot = %s::jsonb, updated_at = NOW() WHERE id = %s",
                (snap_json, watch_id),
            )
        n = cur.rowcount
        cur.close()
        conn.commit()
        return n > 0
    except Exception as e:
        logger.debug("update_watch_snapshot failed: %s", e)
        return False
