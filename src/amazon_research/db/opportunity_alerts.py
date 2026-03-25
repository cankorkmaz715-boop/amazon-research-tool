"""
Step 107: Persist opportunity alerts for dashboard and notification rules integration.
Optional: engine produces in-memory alerts; save/list for listing and filtering.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.opportunity_alerts")


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def save_opportunity_alert(
    alert: Dict[str, Any],
    workspace_id: Optional[int] = None,
) -> Optional[int]:
    """
    Persist one opportunity alert (from evaluate_opportunity_alerts). Returns id or None.
    alert must have target_entity, alert_type, triggering_signals, and optionally timestamp.
    """
    entity = (alert.get("target_entity") or "").strip()
    atype = (alert.get("alert_type") or "").strip()
    if not entity or not atype:
        return None
    target_type = (alert.get("target_type") or "cluster").strip() or "cluster"
    signals = alert.get("triggering_signals")
    if not isinstance(signals, dict):
        signals = {}
    try:
        conn = _get_connection()
        cur = conn.cursor()
        signals_json = json.dumps(signals)
        cur.execute(
            """INSERT INTO opportunity_alerts (target_type, target_entity, alert_type, triggering_signals, workspace_id)
               VALUES (%s, %s, %s, %s::jsonb, %s) RETURNING id""",
            (target_type, entity, atype, signals_json, workspace_id),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
        cur.close()
        conn.commit()
        return rid
    except Exception as e:
        logger.debug("save_opportunity_alert failed: %s", e)
        return None


def list_opportunity_alerts(
    limit: int = 50,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List recent opportunity alerts, newest first. Optional filter by workspace_id."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        try:
            if workspace_id is not None:
                cur.execute(
                    """SELECT id, target_type, target_entity, alert_type, triggering_signals, recorded_at, workspace_id, read_at
                       FROM opportunity_alerts WHERE workspace_id = %s ORDER BY recorded_at DESC LIMIT %s""",
                    (workspace_id, max(1, limit)),
                )
            else:
                cur.execute(
                    """SELECT id, target_type, target_entity, alert_type, triggering_signals, recorded_at, workspace_id, read_at
                       FROM opportunity_alerts ORDER BY recorded_at DESC LIMIT %s""",
                    (max(1, limit),),
                )
            rows = cur.fetchall()
            has_read_at = True
        except Exception:
            has_read_at = False
            if workspace_id is not None:
                cur.execute(
                    """SELECT id, target_type, target_entity, alert_type, triggering_signals, recorded_at, workspace_id
                       FROM opportunity_alerts WHERE workspace_id = %s ORDER BY recorded_at DESC LIMIT %s""",
                    (workspace_id, max(1, limit)),
                )
            else:
                cur.execute(
                    """SELECT id, target_type, target_entity, alert_type, triggering_signals, recorded_at, workspace_id
                       FROM opportunity_alerts ORDER BY recorded_at DESC LIMIT %s""",
                    (max(1, limit),),
                )
            rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            sig = row[4]
            if isinstance(sig, str):
                try:
                    sig = json.loads(sig)
                except Exception:
                    sig = {}
            item = {
                "id": row[0],
                "target_type": row[1],
                "target_entity": row[2],
                "alert_type": row[3],
                "triggering_signals": sig or {},
                "recorded_at": row[5],
                "workspace_id": row[6],
            }
            if has_read_at and len(row) > 7:
                item["read_at"] = row[7]
            else:
                item["read_at"] = None
            out.append(item)
        return out
    except Exception as e:
        logger.debug("list_opportunity_alerts failed: %s", e)
        return []


def set_opportunity_alert_read(workspace_id: Optional[int], alert_id: Optional[int]) -> bool:
    """Step 216: Mark alert as read. Returns True if updated. Requires read_at column (migration 039)."""
    if workspace_id is None or alert_id is None:
        return False
    try:
        from datetime import datetime, timezone
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """UPDATE opportunity_alerts SET read_at = %s WHERE id = %s AND workspace_id = %s""",
            (datetime.now(timezone.utc), alert_id, workspace_id),
        )
        n = cur.rowcount
        cur.close()
        conn.commit()
        return n > 0
    except Exception as e:
        logger.debug("set_opportunity_alert_read failed: %s", e)
        return False
