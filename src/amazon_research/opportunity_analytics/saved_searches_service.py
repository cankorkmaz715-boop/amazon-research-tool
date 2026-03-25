"""
Steps 246–248: Saved searches – workspace-scoped. In-memory store (no DB table required for v1).
Fields: label, query, market, category, limit, sort, created_at.
"""
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("opportunity_analytics.saved_searches")

_store: Dict[int, List[Dict[str, Any]]] = {}
_counter = 1
_lock = threading.Lock()


def _now_utc() -> str:
    return datetime.now(timezone.utc()).isoformat()


def list_saved_searches(workspace_id: int) -> List[Dict[str, Any]]:
    """List saved searches for workspace. Returns list of items with id, label, query, market, category, limit, sort, created_at."""
    with _lock:
        items = _store.get(workspace_id) or []
    return list(items)


def create_saved_search(
    workspace_id: int,
    label: str,
    query: str = "",
    market: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    sort: str = "recent",
) -> Dict[str, Any]:
    """Create a saved search. Returns the created item with id and created_at."""
    global _counter
    item = {
        "id": None,
        "label": (label or "Saved search").strip()[:200],
        "query": (query or "").strip()[:500],
        "market": (market or "").strip()[:20] or None,
        "category": (category or "").strip()[:200] or None,
        "limit": max(1, min(limit, 200)),
        "sort": (sort or "recent").strip()[:50] or "recent",
        "created_at": _now_utc(),
    }
    with _lock:
        if workspace_id not in _store:
            _store[workspace_id] = []
        _counter += 1
        item["id"] = _counter
        _store[workspace_id].append(item)
    return dict(item)


def delete_saved_search(workspace_id: int, search_id: int) -> bool:
    """Delete a saved search by id. Returns True if removed."""
    with _lock:
        items = _store.get(workspace_id) or []
        for i, it in enumerate(items):
            if it.get("id") == search_id:
                items.pop(i)
                return True
    return False


def get_saved_search(workspace_id: int, search_id: int) -> Optional[Dict[str, Any]]:
    """Get one saved search by id. Returns None if not found."""
    with _lock:
        items = _store.get(workspace_id) or []
        for it in items:
            if it.get("id") == search_id:
                return dict(it)
    return None
