"""
Step 146: Conversational research threading – link related copilot sessions into threads.
Supports follow-up on same niche/ASIN/cluster and continued exploration. Lightweight, rule-based.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.conversational_threading")

# In-memory thread store (process lifetime). Keys: thread_id.
_THREADS: Dict[str, Dict[str, Any]] = {}
_THREAD_ORDER: List[str] = []  # creation order for list_threads (newest last)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_thread(
    *,
    session_ids: Optional[List[str]] = None,
    topic: Optional[str] = None,
    anchor: Optional[str] = None,
    workspace_id: Optional[int] = None,
    thread_id: Optional[str] = None,
) -> Optional[str]:
    """
    Create a thread linking related research sessions. Represents follow-up on same niche/ASIN/cluster
    or continued exploration from a previous session.
    Returns thread_id.
    """
    tid = (thread_id or "").strip() or f"thread-{uuid.uuid4().hex[:12]}"
    sids = [s for s in (session_ids or []) if s and isinstance(s, str)]
    now = _ts()
    _THREADS[tid] = {
        "thread_id": tid,
        "linked_session_ids": sids,
        "thread_topic": (topic or "").strip() or None,
        "thread_anchor": (anchor or "").strip() or None,
        "workspace_id": workspace_id,
        "created_at": now,
        "updated_at": now,
    }
    if tid not in _THREAD_ORDER:
        _THREAD_ORDER.append(tid)
    # Optionally link sessions to each other in copilot research memory
    for i, sid in enumerate(sids):
        if i > 0:
            try:
                from amazon_research.discovery.copilot_research_memory import link_sessions
                link_sessions(sids[i - 1], sid, workspace_id=workspace_id)
            except Exception as e:
                logger.debug("create_thread link_sessions: %s", e)
    return tid


def get_thread(thread_id: str, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Return thread by thread_id. Optionally filter by workspace_id."""
    tid = (thread_id or "").strip()
    if not tid or tid not in _THREADS:
        return None
    t = _THREADS[tid]
    if workspace_id is not None and t.get("workspace_id") is not None and t.get("workspace_id") != workspace_id:
        return None
    return {
        "thread_id": tid,
        "linked_session_ids": list(t.get("linked_session_ids") or []),
        "thread_topic": t.get("thread_topic"),
        "thread_anchor": t.get("thread_anchor"),
        "workspace_id": t.get("workspace_id"),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
    }


def add_session_to_thread(thread_id: str, session_id: str, workspace_id: Optional[int] = None) -> bool:
    """Add a session to an existing thread and link to previous session in memory."""
    tid = (thread_id or "").strip()
    sid = (session_id or "").strip()
    if not tid or not sid or tid not in _THREADS:
        return False
    t = _THREADS[tid]
    if workspace_id is not None and t.get("workspace_id") is not None and t.get("workspace_id") != workspace_id:
        return False
    sids = list(t.get("linked_session_ids") or [])
    if sid in sids:
        return True
    sids.append(sid)
    t["linked_session_ids"] = sids
    t["updated_at"] = _ts()
    if len(sids) >= 2:
        try:
            from amazon_research.discovery.copilot_research_memory import link_sessions
            link_sessions(sids[-2], sid, workspace_id=workspace_id)
        except Exception as e:
            logger.debug("add_session_to_thread link_sessions: %s", e)
    return True


def list_threads(
    workspace_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List threads newest first. Optionally filter by workspace_id."""
    order = [t for t in reversed(_THREAD_ORDER) if t in _THREADS]
    if workspace_id is not None:
        order = [t for t in order if _THREADS[t].get("workspace_id") in (None, workspace_id)]
    slice_ids = order[offset : offset + limit]
    out = []
    for tid in slice_ids:
        rec = get_thread(tid, workspace_id=workspace_id)
        if rec:
            out.append(rec)
    return out


def get_thread_summary(thread_id: str, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Produce structured thread output: thread_id, linked_session_ids, thread_summary/topic, latest_session_reference.
    Topic/summary is derived from thread_topic or first session's query/intent when available.
    """
    t = get_thread(thread_id, workspace_id=workspace_id)
    if not t:
        return None
    sids = t.get("linked_session_ids") or []
    topic = t.get("thread_topic") or t.get("thread_anchor") or ""
    if not topic and sids:
        try:
            from amazon_research.discovery.copilot_research_memory import get_session
            first = get_session(sids[0], workspace_id=workspace_id)
            if first:
                q = (first.get("copilot_query") or "").strip()
                intent = (first.get("interpreted_intent") or "").strip()
                if q:
                    topic = q[:80] + ("..." if len(q) > 80 else "")
                elif intent:
                    topic = intent.replace("_", " ")
        except Exception as e:
            logger.debug("get_thread_summary get_session: %s", e)
    if not topic:
        topic = f"Thread with {len(sids)} session(s)"
    latest = sids[-1] if sids else None
    return {
        "thread_id": t.get("thread_id"),
        "linked_session_ids": sids,
        "thread_summary": topic,
        "thread_topic": topic,
        "latest_session_reference": latest,
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
    }
