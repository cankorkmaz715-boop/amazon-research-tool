"""
Step 236: Opportunity feed persistence – DB access for current and history.
Workspace-scoped; safe upsert for current; append-only for history.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("opportunity_persistence.repository")


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def upsert_current(workspace_id: int, opportunity_ref: str, payload: Dict[str, Any]) -> bool:
    """Upsert one row in opportunity_feed_current. Returns True on success."""
    ref = (opportunity_ref or "").strip()
    if not ref or workspace_id is None:
        return False
    try:
        conn = _get_connection()
        cur = conn.cursor()
        now = _now_utc()
        payload_json = json.dumps(payload if isinstance(payload, dict) else {})
        cur.execute(
            """INSERT INTO opportunity_feed_current (workspace_id, opportunity_ref, payload_json, observed_at, created_at, updated_at)
               VALUES (%s, %s, %s::jsonb, %s, %s, %s)
               ON CONFLICT (workspace_id, opportunity_ref)
               DO UPDATE SET payload_json = EXCLUDED.payload_json, observed_at = EXCLUDED.observed_at, updated_at = EXCLUDED.updated_at""",
            (workspace_id, ref, payload_json, now, now, now),
        )
        cur.close()
        conn.commit()
        return True
    except Exception as e:
        logger.warning("opportunity_persistence upsert_current failed workspace_id=%s ref=%s: %s", workspace_id, ref[:50], e)
        return False


def list_current_for_workspace(workspace_id: Optional[int], limit: int = 200) -> List[Dict[str, Any]]:
    """List current feed rows for workspace, ordered by updated_at DESC. Returns [] on error or empty."""
    if workspace_id is None:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT workspace_id, opportunity_ref, payload_json, observed_at, created_at, updated_at
               FROM opportunity_feed_current
               WHERE workspace_id = %s
               ORDER BY updated_at DESC
               LIMIT %s""",
            (workspace_id, max(1, min(limit, 500))),
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for r in rows:
            payload = r[2]
            if isinstance(payload, str) and payload:
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            if not isinstance(payload, dict):
                payload = {}
            out.append({
                "workspace_id": r[0],
                "opportunity_ref": r[1],
                "payload_json": payload,
                "observed_at": r[3],
                "created_at": r[4],
                "updated_at": r[5],
            })
        return out
    except Exception as e:
        logger.warning("opportunity_persistence list_current_for_workspace failed workspace_id=%s: %s", workspace_id, e)
        return []


def insert_history(workspace_id: int, opportunity_ref: str, payload: Dict[str, Any], observed_at: Optional[datetime] = None) -> bool:
    """Append one row to opportunity_feed_history. Returns True on success."""
    ref = (opportunity_ref or "").strip()
    if not ref or workspace_id is None:
        return False
    try:
        conn = _get_connection()
        cur = conn.cursor()
        now = observed_at or _now_utc()
        payload_json = json.dumps(payload if isinstance(payload, dict) else {})
        cur.execute(
            """INSERT INTO opportunity_feed_history (workspace_id, opportunity_ref, payload_json, observed_at, created_at)
               VALUES (%s, %s, %s::jsonb, %s, %s)""",
            (workspace_id, ref, payload_json, now, _now_utc()),
        )
        cur.close()
        conn.commit()
        return True
    except Exception as e:
        logger.warning("opportunity_persistence insert_history failed workspace_id=%s ref=%s: %s", workspace_id, ref[:50], e)
        return False


def list_history_for_ref(
    workspace_id: Optional[int],
    opportunity_ref: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List history rows for a single opportunity ref in workspace. Newest first. Returns [] on error or empty."""
    ref = (opportunity_ref or "").strip()
    if not ref or workspace_id is None:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, opportunity_ref, payload_json, observed_at, created_at
               FROM opportunity_feed_history
               WHERE workspace_id = %s AND opportunity_ref = %s
               ORDER BY observed_at DESC
               LIMIT %s""",
            (workspace_id, ref, max(1, min(limit, 200))),
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for r in rows:
            payload = r[3]
            if isinstance(payload, str) and payload:
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            if not isinstance(payload, dict):
                payload = {}
            out.append({
                "id": r[0],
                "workspace_id": r[1],
                "opportunity_ref": r[2],
                "payload_json": payload,
                "observed_at": r[4],
                "created_at": r[5],
            })
        return out
    except Exception as e:
        logger.warning("opportunity_persistence list_history_for_ref failed workspace_id=%s ref=%s: %s", workspace_id, ref[:50], e)
        return []


def list_history_for_workspace(workspace_id: Optional[int], limit: int = 50) -> List[Dict[str, Any]]:
    """List recent history rows for workspace, newest first. Returns [] on error or empty."""
    if workspace_id is None:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, opportunity_ref, payload_json, observed_at, created_at
               FROM opportunity_feed_history
               WHERE workspace_id = %s
               ORDER BY observed_at DESC
               LIMIT %s""",
            (workspace_id, max(1, min(limit, 200))),
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for r in rows:
            payload = r[3]
            if isinstance(payload, str) and payload:
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            if not isinstance(payload, dict):
                payload = {}
            out.append({
                "id": r[0],
                "workspace_id": r[1],
                "opportunity_ref": r[2],
                "payload_json": payload,
                "observed_at": r[4],
                "created_at": r[5],
            })
        return out
    except Exception as e:
        logger.warning("opportunity_persistence list_history_for_workspace failed workspace_id=%s: %s", workspace_id, e)
        return []
