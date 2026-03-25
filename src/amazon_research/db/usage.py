"""
Workspace usage tracking v1. Step 53 – discovery, refresh, scoring, export, API access.
Compact records; no quota or billing. workspace_id NULL for system-level (e.g. pipeline).
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.usage")

EVENT_DISCOVERY_RUN = "discovery_run"
EVENT_REFRESH_RUN = "refresh_run"
EVENT_SCORING_RUN = "scoring_run"
EVENT_EXPORT_CSV = "export_csv"
EVENT_EXPORT_JSON = "export_json"
EVENT_API_PRODUCTS = "api_products"
EVENT_API_METRICS = "api_metrics"
EVENT_API_SCORES = "api_scores"
EVENT_API_SAVED_VIEWS = "api_saved_views"
EVENT_API_WATCHLISTS = "api_watchlists"
EVENT_API_WATCHLIST_ITEMS = "api_watchlist_items"


def record_usage(
    workspace_id: Optional[int],
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Record a usage event. workspace_id may be None for system-level (e.g. pipeline runs).
    event_type: discovery_run, refresh_run, scoring_run, export_csv, export_json, api_*.
    payload: optional compact dict (e.g. {"pages": 3, "asins": 5}).
    """
    conn = get_connection()
    cur = conn.cursor()
    payload_json = json.dumps(payload) if payload else None
    cur.execute(
        """
        INSERT INTO workspace_usage_events (workspace_id, event_type, payload)
        VALUES (%s, %s, %s::jsonb)
        """,
        (workspace_id, (event_type or "").strip(), payload_json),
    )
    cur.close()
    conn.commit()


def get_usage_summary(
    workspace_id: Optional[int] = None,
    since_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Return usage summary: list of { workspace_id, event_type, count }.
    If workspace_id given, filter to that workspace. If since_days given, filter to that many days.
    """
    conn = get_connection()
    cur = conn.cursor()
    conditions = []
    params: List[Any] = []
    if workspace_id is not None:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    if since_days is not None and since_days > 0:
        conditions.append("created_at >= NOW() - INTERVAL '1 day' * %s")
        params.append(since_days)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    cur.execute(
        f"""
        SELECT workspace_id, event_type, COUNT(*) AS cnt
        FROM workspace_usage_events
        {where}
        GROUP BY workspace_id, event_type
        ORDER BY workspace_id NULLS LAST, event_type
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"workspace_id": r[0], "event_type": r[1], "count": r[2]}
        for r in rows
    ]


def get_usage_summary_for_workspace(
    workspace_id: int,
    since_days: Optional[int] = None,
) -> Dict[str, int]:
    """
    Return a simple dict of event_type -> count for one workspace. Easy to summarize.
    """
    rows = get_usage_summary(workspace_id=workspace_id, since_days=since_days)
    return {r["event_type"]: r["count"] for r in rows}
