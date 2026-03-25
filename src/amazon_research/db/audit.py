"""
Audit logs v1. Step 56 – record important actions; lightweight and non-blocking.
Event types: discovery_run, refresh_run, export_csv, export_json, quota_exceeded, api_*.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.audit")


def record_audit(
    workspace_id: Optional[int],
    event_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append one audit log entry. Non-blocking: logs and swallows DB errors so callers are not failed.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        meta_json = json.dumps(metadata) if metadata else None
        cur.execute(
            """
            INSERT INTO audit_logs (workspace_id, event_type, metadata)
            VALUES (%s, %s, %s::jsonb)
            """,
            (workspace_id, (event_type or "").strip(), meta_json),
        )
        cur.close()
        conn.commit()
    except Exception as e:
        logger.warning("audit log write failed (non-blocking)", extra={"event_type": event_type, "error": str(e)})


def list_audit_logs(
    workspace_id: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Return recent audit log entries, optionally filtered by workspace_id. For tests and admin."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        if workspace_id is not None:
            cur.execute(
                """
                SELECT id, workspace_id, event_type, created_at, metadata
                FROM audit_logs WHERE workspace_id = %s ORDER BY created_at DESC LIMIT %s
                """,
                (workspace_id, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, workspace_id, event_type, created_at, metadata
                FROM audit_logs ORDER BY created_at DESC LIMIT %s
                """,
                (limit,),
            )
        rows = cur.fetchall()
        cur.close()
        return [
            {"id": r[0], "workspace_id": r[1], "event_type": r[2], "created_at": r[3], "metadata": r[4]}
            for r in rows
        ]
    except Exception as e:
        logger.warning("audit log list failed", extra={"error": str(e)})
        return []
