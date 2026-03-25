"""
Step 116: Tenant analytics snapshots – store and retrieve workspace-level analytics snapshot history.
Append-only; history-friendly.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.tenant_analytics_snapshots")


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def save_tenant_snapshot(
    workspace_id: int,
    payload: Dict[str, Any],
    *,
    since_days: Optional[int] = None,
) -> Optional[int]:
    """Append one snapshot. Returns snapshot id or None."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        payload_json = json.dumps(payload) if payload else "{}"
        cur.execute(
            """INSERT INTO tenant_analytics_snapshots (workspace_id, payload, since_days)
               VALUES (%s, %s::jsonb, %s) RETURNING id""",
            (workspace_id, payload_json, since_days),
        )
        row = cur.fetchone()
        sid = row[0] if row else None
        cur.close()
        conn.commit()
        return sid
    except Exception as e:
        logger.debug("save_tenant_snapshot failed: %s", e)
        return None


def get_latest_snapshot(workspace_id: int) -> Optional[Dict[str, Any]]:
    """Return the most recent snapshot for the workspace (id, workspace_id, snapshot_at, since_days, payload)."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, snapshot_at, since_days, payload
               FROM tenant_analytics_snapshots
               WHERE workspace_id = %s
               ORDER BY snapshot_at DESC
               LIMIT 1""",
            (workspace_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        payload = row[4]
        if isinstance(payload, str) and payload:
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        return {
            "id": row[0],
            "workspace_id": row[1],
            "snapshot_at": row[2],
            "since_days": row[3],
            "payload": payload or {},
        }
    except Exception as e:
        logger.debug("get_latest_snapshot failed: %s", e)
        return None


def get_snapshot_history(
    workspace_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return snapshot history for the workspace, newest first."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, snapshot_at, since_days, payload
               FROM tenant_analytics_snapshots
               WHERE workspace_id = %s
               ORDER BY snapshot_at DESC
               LIMIT %s""",
            (workspace_id, max(1, limit)),
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            payload = row[4]
            if isinstance(payload, str) and payload:
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            out.append({
                "id": row[0],
                "workspace_id": row[1],
                "snapshot_at": row[2],
                "since_days": row[3],
                "payload": payload or {},
            })
        return out
    except Exception as e:
        logger.debug("get_snapshot_history failed: %s", e)
        return []
