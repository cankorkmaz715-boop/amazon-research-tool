"""
Step 236: Map persisted current/history rows to feed-item shape for API/dashboard.
"""
from typing import Any, Dict, List

from amazon_research.opportunity_persistence.opportunity_persistence_types import payload_to_feed_item


def current_rows_to_feed_items(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert list_current_for_workspace rows into feed items (stable shape for GET opportunities)."""
    out: List[Dict[str, Any]] = []
    for r in rows:
        payload = r.get("payload_json") or r.get("payload") or {}
        observed = r.get("observed_at")
        observed_str = observed.isoformat() if hasattr(observed, "isoformat") else str(observed) if observed else None
        item = payload_to_feed_item(payload, observed_at=observed_str)
        if not item:
            continue
        if "opportunity_id" not in item and r.get("opportunity_ref"):
            item["opportunity_id"] = r.get("opportunity_ref")
        out.append(item)
    return out


def history_rows_to_feed_items(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert list_history_for_workspace rows into feed-item-like dicts with observed_at."""
    out: List[Dict[str, Any]] = []
    for r in rows:
        payload = r.get("payload_json") or r.get("payload") or {}
        observed = r.get("observed_at")
        observed_str = observed.isoformat() if hasattr(observed, "isoformat") else str(observed) if observed else None
        item = payload_to_feed_item(payload, observed_at=observed_str)
        if not item:
            continue
        if "opportunity_id" not in item and r.get("opportunity_ref"):
            item["opportunity_id"] = r.get("opportunity_ref")
        item["observed_at"] = observed_str
        out.append(item)
    return out
