"""
Step 145: Copilot research memory (discovery layer) – store and link copilot-driven research sessions.
Uses db.copilot_research_memory for persistence. Compatible with copilot, planner, guided execution, insight summarizer.
"""
import uuid
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.copilot_research_memory")


def store_session(
    *,
    session_id: Optional[str] = None,
    workspace_id: Optional[int] = None,
    copilot_query: Optional[str] = None,
    interpreted_intent: Optional[str] = None,
    research_plan_ref: Optional[str] = None,
    guided_execution_ref: Optional[str] = None,
    insight_summary_ref: Optional[str] = None,
    suggested_next_steps_ref: Optional[List[str]] = None,
    plan: Optional[Dict[str, Any]] = None,
    execution_output: Optional[Dict[str, Any]] = None,
    insight_summary: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Store a copilot research session. If session_id is omitted, one is generated.
    Refs can be passed directly or extracted from plan, execution_output, insight_summary.
    Returns session_id or None.
    """
    sid = (session_id or "").strip() or f"copilot-{uuid.uuid4().hex[:12]}"
    plan_ref = research_plan_ref
    exec_ref = guided_execution_ref
    summary_ref = insight_summary_ref
    next_refs = suggested_next_steps_ref if isinstance(suggested_next_steps_ref, list) else None
    intent = interpreted_intent
    query = copilot_query

    if plan and not plan_ref:
        plan_ref = plan.get("plan_id")
    if plan and intent is None:
        intent = plan.get("interpreted_intent")
    if execution_output and not exec_ref:
        exec_ref = execution_output.get("plan_id") or execution_output.get("execution_id")
    if insight_summary:
        if not summary_ref:
            summary_ref = insight_summary.get("summary_id")
        if next_refs is None and insight_summary.get("suggested_next_steps"):
            next_refs = [s[:200] for s in insight_summary.get("suggested_next_steps")][:10]

    try:
        from amazon_research.db import save_copilot_session
        save_copilot_session(
            sid,
            workspace_id=workspace_id,
            copilot_query=query,
            interpreted_intent=intent,
            research_plan_ref=plan_ref,
            guided_execution_ref=exec_ref,
            insight_summary_ref=summary_ref,
            suggested_next_steps_ref=next_refs or [],
        )
        return sid
    except Exception as e:
        logger.debug("store_session failed: %s", e)
        return None


def get_session(session_id: str, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Return one session by session_id. Optionally filter by workspace_id."""
    try:
        from amazon_research.db import get_copilot_session
        return get_copilot_session(session_id, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("get_session failed: %s", e)
        return None


def list_sessions(
    workspace_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List sessions newest first. Optionally filter by workspace_id."""
    try:
        from amazon_research.db import list_copilot_sessions
        return list_copilot_sessions(workspace_id=workspace_id, limit=limit, offset=offset)
    except Exception as e:
        logger.debug("list_sessions failed: %s", e)
        return []


def link_sessions(session_id: str, related_session_id: str, workspace_id: Optional[int] = None) -> bool:
    """Link two sessions: add related_session_id to session_id's related_session_ids."""
    try:
        from amazon_research.db import link_copilot_sessions
        return link_copilot_sessions(session_id, related_session_id, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("link_sessions failed: %s", e)
        return False
