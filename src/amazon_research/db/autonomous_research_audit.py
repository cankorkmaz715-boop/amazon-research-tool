"""
Step 139: Autonomous research audit – persist and retrieve audit records for controlled autonomous runs.
Append-only; payload stores run_id, actions, safety, opportunities, timestamps.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.autonomous_research_audit")


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def save_autonomous_run_audit(
    run_id: str,
    payload: Dict[str, Any],
    workspace_id: Optional[int] = None,
) -> Optional[int]:
    """Append one audit record. run_id and payload required. Returns audit id or None."""
    run_id = (run_id or "").strip()
    if not run_id:
        return None
    if not isinstance(payload, dict):
        payload = {}
    try:
        conn = _get_connection()
        cur = conn.cursor()
        payload_json = json.dumps(payload)
        cur.execute(
            """INSERT INTO autonomous_research_audit (run_id, workspace_id, payload)
               VALUES (%s, %s, %s::jsonb) RETURNING id""",
            (run_id, workspace_id, payload_json),
        )
        row = cur.fetchone()
        aid = row[0] if row else None
        cur.close()
        conn.commit()
        return aid
    except Exception as e:
        logger.debug("save_autonomous_run_audit failed: %s", e)
        return None


def get_audit_for_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Return the audit record for the given run_id (id, run_id, workspace_id, payload, created_at)."""
    run_id = (run_id or "").strip()
    if not run_id:
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, run_id, workspace_id, payload, created_at
               FROM autonomous_research_audit WHERE run_id = %s ORDER BY created_at DESC LIMIT 1""",
            (run_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        payload = row[3]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        return {
            "id": row[0],
            "run_id": row[1],
            "workspace_id": row[2],
            "payload": payload if isinstance(payload, dict) else {},
            "created_at": row[4],
        }
    except Exception as e:
        logger.debug("get_audit_for_run failed: %s", e)
        return None


def get_audit_trail(
    workspace_id: Optional[int] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return audit records newest first. Optional workspace_id filter."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if workspace_id is not None:
            cur.execute(
                """SELECT id, run_id, workspace_id, payload, created_at
                   FROM autonomous_research_audit WHERE workspace_id = %s ORDER BY created_at DESC LIMIT %s""",
                (workspace_id, max(1, limit)),
            )
        else:
            cur.execute(
                """SELECT id, run_id, workspace_id, payload, created_at
                   FROM autonomous_research_audit ORDER BY created_at DESC LIMIT %s""",
                (max(1, limit),),
            )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            payload = row[3]
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            out.append({
                "id": row[0],
                "run_id": row[1],
                "workspace_id": row[2],
                "payload": payload if isinstance(payload, dict) else {},
                "created_at": row[4],
            })
        return out
    except Exception as e:
        logger.debug("get_audit_trail failed: %s", e)
        return []
