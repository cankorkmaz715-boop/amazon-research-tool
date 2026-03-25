"""
Step 199: Workspace activity log persistence – structured workspace events.
Non-blocking: failures must not crash callers.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.workspace_activity_log")

EVENT_TYPES = frozenset({
    "intelligence_refresh", "configuration_updated", "portfolio_item_added", "portfolio_item_archived",
    "alert_preferences_updated", "snapshot_persisted", "cache_refreshed", "fallback_triggered",
    "strategy_refresh",
    "portfolio_recommendation_refresh",
    "market_entry_signals_refresh",
    "risk_detection_refresh",
    "strategic_scoring_refresh",
})
SEVERITY_VALUES = frozenset({"info", "warning", "error"})


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _safe_payload(val: Any) -> Dict[str, Any]:
    if val is None:
        return {}
    if isinstance(val, dict):
        return dict(val)
    if isinstance(val, str) and val.strip():
        try:
            out = json.loads(val)
            return dict(out) if isinstance(out, dict) else {}
        except Exception:
            return {}
    return {}


def create_workspace_activity_event(
    workspace_id: int,
    event_type: str,
    event_label: Optional[str] = None,
    actor_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    source_module: Optional[str] = None,
    event_payload: Optional[Dict[str, Any]] = None,
    severity: str = "info",
) -> Optional[int]:
    """
    Insert one activity log entry. Returns event id or None on error.
    Defensive: event_type/severity normalized; invalid payload becomes {}.
    Logs create start, success, failure. Callers must not depend on success – non-blocking.
    """
    if workspace_id is None:
        return None
    etype = (event_type or "").strip() or "configuration_updated"
    if etype not in EVENT_TYPES:
        etype = "configuration_updated"
    sev = (severity or "info").strip().lower()
    if sev not in SEVERITY_VALUES:
        sev = "info"
    label = (event_label or "").strip() or None
    atype = (actor_type or "").strip() or None
    aid = (actor_id or "").strip() or None
    smod = (source_module or "").strip() or None
    payload = _safe_payload(event_payload)
    payload_json = json.dumps(payload)
    logger.info("workspace_activity_log create start workspace_id=%s event_type=%s source_module=%s", workspace_id, etype, smod)
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO workspace_activity_log
               (workspace_id, event_type, event_label, actor_type, actor_id, source_module, event_payload_json, severity, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, NOW())
               RETURNING id""",
            (workspace_id, etype, label, atype, aid, smod, payload_json, sev),
        )
        row = cur.fetchone()
        cur.close()
        conn.commit()
        if row:
            logger.info("workspace_activity_log create success workspace_id=%s id=%s event_type=%s", workspace_id, row[0], etype)
            return row[0]
    except Exception as e:
        logger.warning("workspace_activity_log create failure workspace_id=%s event_type=%s: %s", workspace_id, etype, e)
    return None


def list_workspace_activity_events(
    workspace_id: Optional[int],
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List recent activity events for workspace. Returns [] on error or no workspace_id."""
    if workspace_id is None:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        conditions = ["workspace_id = %s"]
        params: List[Any] = [workspace_id]
        if event_type and (event_type or "").strip() in EVENT_TYPES:
            conditions.append("event_type = %s")
            params.append((event_type or "").strip())
        if severity and (severity or "").strip().lower() in SEVERITY_VALUES:
            conditions.append("severity = %s")
            params.append((severity or "").strip().lower())
        params.append(max(1, min(500, limit)))
        cur.execute(
            f"""SELECT id, workspace_id, event_type, event_label, actor_type, actor_id, source_module, event_payload_json, severity, created_at
                FROM workspace_activity_log
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT %s""",
            params,
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for r in rows:
            pl = r[7]
            if isinstance(pl, str) and pl:
                try:
                    pl = json.loads(pl)
                except Exception:
                    pl = {}
            if not isinstance(pl, dict):
                pl = {}
            out.append({
                "id": r[0],
                "workspace_id": r[1],
                "event_type": r[2],
                "event_label": r[3],
                "actor_type": r[4],
                "actor_id": r[5],
                "source_module": r[6],
                "event_payload_json": pl,
                "severity": r[8],
                "created_at": r[9],
            })
        logger.info("workspace_activity_log list read workspace_id=%s count=%s", workspace_id, len(out))
        return out
    except Exception as e:
        logger.warning("workspace_activity_log list failed workspace_id=%s: %s", workspace_id, e)
        return []


def get_workspace_activity_summary(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Summary counts by event_type and severity. Stable shape; empty counts when no events or on error."""
    out: Dict[str, Any] = {"workspace_id": workspace_id, "total": 0, "by_event_type": {}, "by_severity": {"info": 0, "warning": 0, "error": 0}}
    if workspace_id is None:
        return out
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT event_type, severity, COUNT(*) FROM workspace_activity_log
               WHERE workspace_id = %s GROUP BY event_type, severity""",
            (workspace_id,),
        )
        rows = cur.fetchall()
        cur.close()
        total = 0
        for r in rows:
            et, sev, c = r[0], r[1], int(r[2])
            total += c
            out["by_event_type"][et] = out["by_event_type"].get(et, 0) + c
            out["by_severity"][sev] = out["by_severity"].get(sev, 0) + c
        out["total"] = total
        logger.info("workspace_activity_log summary read workspace_id=%s total=%s", workspace_id, total)
    except Exception as e:
        logger.warning("workspace_activity_log summary failed workspace_id=%s: %s", workspace_id, e)
    return out
