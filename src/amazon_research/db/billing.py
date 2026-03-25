"""
Billing hooks v1. Step 58 – record billable events for future billing integration.
Non-blocking; no payment provider. Reuses workspace and usage/audit concepts.
Event types: usage_summary, export_csv, export_json, api_request, quota_overage.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection
from .usage import get_usage_summary_for_workspace

logger = get_logger("db.billing")


def record_billable_event(
    workspace_id: int,
    event_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Record one billable event. Step 60: injects plan_id and plan_name when workspace has a plan.
    Non-blocking: logs and swallows DB errors.
    """
    try:
        meta = dict(metadata) if metadata else {}
        try:
            from .plans import get_workspace_plan
            plan = get_workspace_plan(workspace_id)
            if plan:
                meta["plan_id"] = plan.get("id")
                meta["plan_name"] = plan.get("name")
        except Exception:
            pass
        conn = get_connection()
        cur = conn.cursor()
        meta_json = json.dumps(meta) if meta else None
        cur.execute(
            """
            INSERT INTO billable_events (workspace_id, event_type, metadata)
            VALUES (%s, %s, %s::jsonb)
            """,
            (workspace_id, (event_type or "").strip(), meta_json),
        )
        cur.close()
        conn.commit()
    except Exception as e:
        logger.warning("billable event write failed (non-blocking)", extra={"event_type": event_type, "error": str(e)})


def get_billable_events_summary(
    workspace_id: int,
    since_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Return aggregated billable events for the workspace: list of { event_type, count }.
    For future billing provider or internal reporting.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        if since_days is not None and since_days > 0:
            cur.execute(
                """
                SELECT event_type, COUNT(*) AS cnt
                FROM billable_events
                WHERE workspace_id = %s AND created_at >= NOW() - INTERVAL '1 day' * %s
                GROUP BY event_type
                ORDER BY event_type
                """,
                (workspace_id, since_days),
            )
        else:
            cur.execute(
                """
                SELECT event_type, COUNT(*) AS cnt
                FROM billable_events
                WHERE workspace_id = %s
                GROUP BY event_type
                ORDER BY event_type
                """,
                (workspace_id,),
            )
        rows = cur.fetchall()
        cur.close()
        return [{"event_type": r[0], "count": r[1]} for r in rows]
    except Exception as e:
        logger.warning("billable events summary failed", extra={"error": str(e)})
        return []


def record_usage_summary_billable(
    workspace_id: int,
    since_days: int = 30,
) -> None:
    """
    Billing summary hook: fetch workspace usage and record one usage_summary billable event.
    Non-blocking. Call periodically or on-demand for billing reconciliation.
    """
    try:
        usage = get_usage_summary_for_workspace(workspace_id, since_days=since_days)
        record_billable_event(
            workspace_id,
            "usage_summary",
            {"since_days": since_days, "usage": usage},
        )
    except Exception as e:
        logger.warning("usage_summary billable failed (non-blocking)", extra={"workspace_id": workspace_id, "error": str(e)})
