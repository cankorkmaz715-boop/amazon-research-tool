"""
Step 236: Opportunity persistence service – persist feed snapshot, read from persistence.
Prefers persisted current for feed read when available; fallback to compute then persist.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from amazon_research.opportunity_persistence.opportunity_persistence_types import feed_item_to_payload
from amazon_research.opportunity_persistence.opportunity_history_repository import (
    upsert_current,
    list_current_for_workspace,
    insert_history,
    list_history_for_workspace,
)
from amazon_research.opportunity_persistence.opportunity_snapshot_mapper import (
    current_rows_to_feed_items,
    history_rows_to_feed_items,
)

logger = get_logger("opportunity_persistence.service")


def persist_feed_snapshot(workspace_id: Optional[int], feed_items: List[Dict[str, Any]], write_history: bool = True) -> bool:
    """
    Persist feed items to opportunity_feed_current (upsert) and optionally append to opportunity_feed_history.
    Returns True if at least one write succeeded. Non-blocking best-effort per item.
    """
    if workspace_id is None or not feed_items:
        return False
    now = datetime.now(timezone.utc)
    any_ok = False
    for item in feed_items:
        ref = (item.get("opportunity_id") or item.get("opportunity_ref") or "").strip()
        if not ref:
            continue
        payload = feed_item_to_payload(item)
        if upsert_current(workspace_id, ref, payload):
            any_ok = True
        if write_history and insert_history(workspace_id, ref, payload, observed_at=now):
            pass
    if any_ok:
        logger.info(
            "opportunity_persistence persist_feed_snapshot workspace_id=%s count=%s",
            workspace_id,
            len(feed_items),
            extra={"workspace_id": workspace_id, "count": len(feed_items)},
        )
    return any_ok


def get_feed_from_persistence(workspace_id: Optional[int], limit: int = 100) -> List[Dict[str, Any]]:
    """
    Read current feed from opportunity_feed_current for workspace.
    Returns list of feed-item-shaped dicts; empty list when no data or on error.
    """
    if workspace_id is None:
        return []
    try:
        rows = list_current_for_workspace(workspace_id, limit=limit)
        if not rows:
            return []
        items = current_rows_to_feed_items(rows)
        logger.debug(
            "opportunity_persistence get_feed_from_persistence workspace_id=%s count=%s",
            workspace_id,
            len(items),
            extra={"workspace_id": workspace_id},
        )
        return items
    except Exception as e:
        logger.warning("opportunity_persistence get_feed_from_persistence failed workspace_id=%s: %s", workspace_id, e)
        return []


def get_opportunity_history_for_workspace(workspace_id: Optional[int], limit: int = 50) -> List[Dict[str, Any]]:
    """Read recent opportunity history for workspace. Returns feed-item-like dicts with observed_at."""
    if workspace_id is None:
        return []
    try:
        rows = list_history_for_workspace(workspace_id, limit=limit)
        return history_rows_to_feed_items(rows)
    except Exception as e:
        logger.warning("opportunity_persistence get_opportunity_history_for_workspace failed workspace_id=%s: %s", workspace_id, e)
        return []
