"""
Steps 249–250: Research sessions – workspace-scoped. In-memory store.
Session fields: id, label, created_at, attached_searches, attached_opportunities, notes_summary.
"""
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("research_workspace.sessions")

_store: Dict[int, List[Dict[str, Any]]] = {}
_counter = 1
_lock = threading.Lock()


def _now_utc() -> str:
    return datetime.now(timezone.utc()).isoformat()


def _session_shape(
    id_: int,
    label: str,
    created_at: str,
    attached_searches: Optional[List[Any]] = None,
    attached_opportunities: Optional[List[Any]] = None,
    notes_summary: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": id_,
        "label": (label or "Research session").strip()[:200],
        "created_at": created_at,
        "attached_searches": list(attached_searches) if isinstance(attached_searches, list) else [],
        "attached_opportunities": list(attached_opportunities) if isinstance(attached_opportunities, list) else [],
        "notes_summary": (notes_summary or "").strip()[:2000] or None,
    }


def list_research_sessions(workspace_id: int) -> List[Dict[str, Any]]:
    """List research sessions for workspace, newest first."""
    with _lock:
        items = _store.get(workspace_id) or []
    return sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)


def create_research_session(
    workspace_id: int,
    label: str = "",
    attached_searches: Optional[List[Any]] = None,
    attached_opportunities: Optional[List[Any]] = None,
    notes_summary: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a research session. Returns the created session."""
    global _counter
    now = _now_utc()
    with _lock:
        if workspace_id not in _store:
            _store[workspace_id] = []
        _counter += 1
        sid = _counter
        session = _session_shape(
            id_=sid,
            label=label or "Research session",
            created_at=now,
            attached_searches=attached_searches,
            attached_opportunities=attached_opportunities,
            notes_summary=notes_summary,
        )
        _store[workspace_id].append(session)
    return dict(session)


def get_research_session(workspace_id: int, session_id: int) -> Optional[Dict[str, Any]]:
    """Get one research session by id. Returns None if not found."""
    with _lock:
        items = _store.get(workspace_id) or []
        for s in items:
            if s.get("id") == session_id:
                return dict(s)
    return None
