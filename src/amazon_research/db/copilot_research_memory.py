"""
Step 145: Copilot research memory – store prior copilot research sessions.
Tracks query, intent, plan ref, execution ref, insight summary ref, next-step refs, related sessions.
Uses DB when available; falls back to persistent in-memory storage so sessions are always storable.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.copilot_research_memory")

# Persistent in-memory fallback when DB is unavailable (process lifetime).
_MEMORY_SESSIONS: Dict[str, Dict[str, Any]] = {}
_MEMORY_ORDER: List[str] = []  # session_id order for list_sessions (newest last for append)


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _memory_session_to_record(sid: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Shape in-memory record like DB _row_to_session output."""
    return {
        "id": data.get("id", hash(sid) % (2 ** 31)),
        "session_id": sid,
        "workspace_id": data.get("workspace_id"),
        "copilot_query": data.get("copilot_query"),
        "interpreted_intent": data.get("interpreted_intent"),
        "research_plan_ref": data.get("research_plan_ref"),
        "guided_execution_ref": data.get("guided_execution_ref"),
        "insight_summary_ref": data.get("insight_summary_ref"),
        "suggested_next_steps_ref": data.get("suggested_next_steps_ref") or [],
        "related_session_ids": data.get("related_session_ids") or [],
        "created_at": data.get("created_at", _now_utc().isoformat()),
        "updated_at": data.get("updated_at", _now_utc().isoformat()),
    }


def save_session(
    session_id: str,
    *,
    workspace_id: Optional[int] = None,
    copilot_query: Optional[str] = None,
    interpreted_intent: Optional[str] = None,
    research_plan_ref: Optional[str] = None,
    guided_execution_ref: Optional[str] = None,
    insight_summary_ref: Optional[str] = None,
    suggested_next_steps_ref: Optional[List[str]] = None,
    related_session_ids: Optional[List[str]] = None,
) -> Optional[int]:
    """
    Insert or update a copilot research session. session_id must be unique.
    Returns row id or None.
    """
    sid = (session_id or "").strip()
    if not sid:
        return None
    next_refs = suggested_next_steps_ref if isinstance(suggested_next_steps_ref, list) else []
    related = related_session_ids if isinstance(related_session_ids, list) else []
    now = _now_utc()

    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO copilot_research_memory
               (session_id, workspace_id, copilot_query, interpreted_intent, research_plan_ref,
                guided_execution_ref, insight_summary_ref, suggested_next_steps_ref, related_session_ids, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
               ON CONFLICT (session_id) DO UPDATE SET
                 workspace_id = COALESCE(EXCLUDED.workspace_id, copilot_research_memory.workspace_id),
                 copilot_query = COALESCE(EXCLUDED.copilot_query, copilot_research_memory.copilot_query),
                 interpreted_intent = COALESCE(EXCLUDED.interpreted_intent, copilot_research_memory.interpreted_intent),
                 research_plan_ref = COALESCE(EXCLUDED.research_plan_ref, copilot_research_memory.research_plan_ref),
                 guided_execution_ref = COALESCE(EXCLUDED.guided_execution_ref, copilot_research_memory.guided_execution_ref),
                 insight_summary_ref = COALESCE(EXCLUDED.insight_summary_ref, copilot_research_memory.insight_summary_ref),
                 suggested_next_steps_ref = CASE WHEN EXCLUDED.suggested_next_steps_ref != '[]'::jsonb THEN EXCLUDED.suggested_next_steps_ref ELSE copilot_research_memory.suggested_next_steps_ref END,
                 related_session_ids = CASE WHEN EXCLUDED.related_session_ids != '[]'::jsonb THEN EXCLUDED.related_session_ids ELSE copilot_research_memory.related_session_ids END,
                 updated_at = EXCLUDED.updated_at
               RETURNING id""",
            (
                sid,
                workspace_id,
                copilot_query,
                interpreted_intent,
                research_plan_ref,
                guided_execution_ref,
                insight_summary_ref,
                json.dumps(next_refs),
                json.dumps(related),
                now,
            ),
        )
        row = cur.fetchone()
        rid = row[0] if row else None
        cur.close()
        conn.commit()
        return rid
    except Exception as e:
        logger.debug("save_session failed (using in-memory): %s", e)
        now_iso = now.isoformat()
        _MEMORY_SESSIONS[sid] = {
            "id": len(_MEMORY_SESSIONS) + 1,
            "workspace_id": workspace_id,
            "copilot_query": copilot_query,
            "interpreted_intent": interpreted_intent,
            "research_plan_ref": research_plan_ref,
            "guided_execution_ref": guided_execution_ref,
            "insight_summary_ref": insight_summary_ref,
            "suggested_next_steps_ref": next_refs,
            "related_session_ids": related,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        if sid not in _MEMORY_ORDER:
            _MEMORY_ORDER.append(sid)
        return _MEMORY_SESSIONS[sid]["id"]


def get_session(session_id: str, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Return one session by session_id. Optionally filter by workspace_id."""
    sid = (session_id or "").strip()
    if not sid:
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if workspace_id is not None:
            cur.execute(
                """SELECT id, session_id, workspace_id, copilot_query, interpreted_intent, research_plan_ref,
                          guided_execution_ref, insight_summary_ref, suggested_next_steps_ref, related_session_ids,
                          created_at, updated_at
                   FROM copilot_research_memory WHERE session_id = %s AND (workspace_id IS NULL OR workspace_id = %s)""",
                (sid, workspace_id),
            )
        else:
            cur.execute(
                """SELECT id, session_id, workspace_id, copilot_query, interpreted_intent, research_plan_ref,
                          guided_execution_ref, insight_summary_ref, suggested_next_steps_ref, related_session_ids,
                          created_at, updated_at
                   FROM copilot_research_memory WHERE session_id = %s""",
                (sid,),
            )
        row = cur.fetchone()
        cur.close()
        if row:
            return _row_to_session(row)
    except Exception as e:
        logger.debug("get_session DB failed (checking in-memory): %s", e)
    # Fallback: in-memory
    data = _MEMORY_SESSIONS.get(sid)
    if not data:
        return None
    if workspace_id is not None and data.get("workspace_id") is not None and data.get("workspace_id") != workspace_id:
        return None
    return _memory_session_to_record(sid, data)


def _row_to_session(row: tuple) -> Dict[str, Any]:
    (
        id_,
        session_id,
        workspace_id,
        copilot_query,
        interpreted_intent,
        research_plan_ref,
        guided_execution_ref,
        insight_summary_ref,
        suggested_next_steps_ref,
        related_session_ids,
        created_at,
        updated_at,
    ) = row
    next_refs = suggested_next_steps_ref
    if isinstance(next_refs, str):
        try:
            next_refs = json.loads(next_refs) if next_refs else []
        except Exception:
            next_refs = []
    related = related_session_ids
    if isinstance(related, str):
        try:
            related = json.loads(related) if related else []
        except Exception:
            related = []
    return {
        "id": id_,
        "session_id": session_id,
        "workspace_id": workspace_id,
        "copilot_query": copilot_query,
        "interpreted_intent": interpreted_intent,
        "research_plan_ref": research_plan_ref,
        "guided_execution_ref": guided_execution_ref,
        "insight_summary_ref": insight_summary_ref,
        "suggested_next_steps_ref": next_refs or [],
        "related_session_ids": related or [],
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
        "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at),
    }


def list_sessions(
    workspace_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List sessions newest first. Optionally filter by workspace_id."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if workspace_id is not None:
            cur.execute(
                """SELECT id, session_id, workspace_id, copilot_query, interpreted_intent, research_plan_ref,
                          guided_execution_ref, insight_summary_ref, suggested_next_steps_ref, related_session_ids,
                          created_at, updated_at
                   FROM copilot_research_memory WHERE workspace_id IS NULL OR workspace_id = %s
                   ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (workspace_id, limit, offset),
            )
        else:
            cur.execute(
                """SELECT id, session_id, workspace_id, copilot_query, interpreted_intent, research_plan_ref,
                          guided_execution_ref, insight_summary_ref, suggested_next_steps_ref, related_session_ids,
                          created_at, updated_at
                   FROM copilot_research_memory ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (limit, offset),
            )
        rows = cur.fetchall()
        cur.close()
        return [_row_to_session(r) for r in rows]
    except Exception as e:
        logger.debug("list_sessions DB failed (using in-memory): %s", e)
    # Fallback: in-memory (newest first: _MEMORY_ORDER is append order, so reverse)
    order = [s for s in reversed(_MEMORY_ORDER) if s in _MEMORY_SESSIONS]
    if workspace_id is not None:
        order = [s for s in order if _MEMORY_SESSIONS.get(s, {}).get("workspace_id") in (None, workspace_id)]
    slice_ids = order[offset : offset + limit]
    return [_memory_session_to_record(sid, _MEMORY_SESSIONS[sid]) for sid in slice_ids]


def link_sessions(session_id: str, related_session_id: str, workspace_id: Optional[int] = None) -> bool:
    """Add related_session_id to session_id's related_session_ids. Both must exist."""
    sid = (session_id or "").strip()
    rid = (related_session_id or "").strip()
    if not sid or not rid or sid == rid:
        return False
    rec = get_session(sid, workspace_id=workspace_id)
    if not rec:
        return False
    related = list(rec.get("related_session_ids") or [])
    if rid in related:
        return True
    related.append(rid)
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE copilot_research_memory SET related_session_ids = %s::jsonb, updated_at = %s WHERE session_id = %s",
            (json.dumps(related), _now_utc(), sid),
        )
        n = cur.rowcount
        cur.close()
        conn.commit()
        return n > 0
    except Exception as e:
        logger.debug("link_sessions DB failed (using in-memory): %s", e)
    # Fallback: update in-memory
    if sid in _MEMORY_SESSIONS:
        _MEMORY_SESSIONS[sid]["related_session_ids"] = related
        _MEMORY_SESSIONS[sid]["updated_at"] = _now_utc().isoformat()
        return True
    return False
