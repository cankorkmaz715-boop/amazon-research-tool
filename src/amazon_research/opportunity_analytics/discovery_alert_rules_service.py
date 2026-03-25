"""
Steps 246–248: Discovery alert rules – workspace-scoped. In-memory store (no DB table required for v1).
Fields: keyword, market, category, min_score, min_opportunity_count, enabled.
"""
import threading
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("opportunity_analytics.discovery_alert_rules")

_store: Dict[int, List[Dict[str, Any]]] = {}
_counter = 1
_lock = threading.Lock()


def list_discovery_alert_rules(workspace_id: int) -> List[Dict[str, Any]]:
    """List discovery alert rules for workspace."""
    with _lock:
        items = _store.get(workspace_id) or []
    return list(items)


def create_discovery_alert_rule(
    workspace_id: int,
    keyword: Optional[str] = None,
    market: Optional[str] = None,
    category: Optional[str] = None,
    min_score: Optional[float] = None,
    min_opportunity_count: Optional[int] = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    """Create a discovery alert rule. Returns the created item with id."""
    global _counter
    item = {
        "id": None,
        "keyword": (keyword or "").strip()[:200] or None,
        "market": (market or "").strip()[:20] or None,
        "category": (category or "").strip()[:200] or None,
        "min_score": float(min_score) if min_score is not None else None,
        "min_opportunity_count": max(0, int(min_opportunity_count)) if min_opportunity_count is not None else None,
        "enabled": bool(enabled),
    }
    with _lock:
        if workspace_id not in _store:
            _store[workspace_id] = []
        _counter += 1
        item["id"] = _counter
        _store[workspace_id].append(item)
    return dict(item)


def delete_discovery_alert_rule(workspace_id: int, rule_id: int) -> bool:
    """Delete a discovery alert rule by id. Returns True if removed."""
    with _lock:
        items = _store.get(workspace_id) or []
        for i, it in enumerate(items):
            if it.get("id") == rule_id:
                items.pop(i)
                return True
    return False


def get_discovery_alert_rule(workspace_id: int, rule_id: int) -> Optional[Dict[str, Any]]:
    """Get one rule by id. Returns None if not found."""
    with _lock:
        items = _store.get(workspace_id) or []
        for it in items:
            if it.get("id") == rule_id:
                return dict(it)
    return None
