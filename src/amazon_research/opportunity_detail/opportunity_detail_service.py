"""
Pipeline: Opportunity detail – build detail payload from opportunity_memory + ranking.
GET /api/workspaces/{workspace_id}/opportunities/{opportunity_id}
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("opportunity_detail.service")


def _title_from_memory(mem: Dict[str, Any]) -> str:
    ctx = mem.get("context") or {}
    title = ctx.get("title") or ctx.get("label") or ctx.get("keyword") or ctx.get("product_title")
    if isinstance(title, str) and title.strip():
        return title.strip()[:200]
    ref = mem.get("opportunity_ref") or ""
    return ref[:200] if ref else "Opportunity"


def _priority_from_score(score: Optional[float]) -> str:
    if score is None:
        return "low"
    try:
        s = float(score)
        if s >= 70:
            return "high"
        if s >= 50:
            return "medium"
    except (TypeError, ValueError):
        pass
    return "low"


def _risk_indicator(ranking: Optional[Dict[str, Any]], mem: Dict[str, Any]) -> str:
    notes: List[str] = []
    al = mem.get("alert_summary") or {}
    if isinstance(al, dict) and al.get("count"):
        notes.append("alerts")
    if ranking:
        comp = ranking.get("competition_score")
        if comp is not None:
            try:
                if float(comp) > 70:
                    notes.append("high_competition")
            except (TypeError, ValueError):
                pass
    return ", ".join(notes) if notes else "low"


def get_opportunity_detail(workspace_id: int, opportunity_id: int) -> Optional[Dict[str, Any]]:
    """
    Return opportunity detail payload for API. None if not found or wrong workspace.
    Fields: id, title, score, priority, ranking_position, rationale_summary, recommended_action, risk_indicator, market, category, history.
    """
    try:
        from amazon_research.db import get_opportunity_memory_by_id, get_latest_ranking
        mem = get_opportunity_memory_by_id(opportunity_id, workspace_id=workspace_id)
        if not mem:
            return None
        ref = (mem.get("opportunity_ref") or "").strip()
        ranking = get_latest_ranking(ref) if ref else None
        ctx = mem.get("context") or {}
        score = mem.get("latest_opportunity_score") or (float(ranking["opportunity_score"]) if ranking and ranking.get("opportunity_score") is not None else None)
        return {
            "id": mem.get("id"),
            "title": _title_from_memory(mem),
            "score": score,
            "priority": _priority_from_score(score),
            "ranking_position": ranking.get("rank") if ranking else None,
            "rationale_summary": ctx.get("rationale_summary") or (f"Score {score}" if score is not None else ""),
            "recommended_action": ctx.get("recommended_action") or "Review and track if relevant.",
            "risk_indicator": _risk_indicator(ranking, mem),
            "market": ctx.get("market") or "",
            "category": ctx.get("category") or "",
            "history": mem.get("score_history") or [],
        }
    except Exception as e:
        logger.warning("get_opportunity_detail failed workspace_id=%s opportunity_id=%s: %s", workspace_id, opportunity_id, e)
        return None


def get_opportunity_ref_by_id(workspace_id: int, opportunity_id: int) -> Optional[str]:
    """Return opportunity_ref for this id/workspace, or None."""
    try:
        from amazon_research.db import get_opportunity_memory_by_id
        mem = get_opportunity_memory_by_id(opportunity_id, workspace_id=workspace_id)
        return (mem.get("opportunity_ref") or "").strip() or None
    except Exception:
        return None
