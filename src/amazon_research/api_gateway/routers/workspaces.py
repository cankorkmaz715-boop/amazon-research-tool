"""
Step 231/232: Workspace-scoped API routes – dashboard, opportunities, portfolio, portfolio summary, alerts, strategy summary. Reuses existing handlers.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query

from amazon_research.logging_config import get_logger

logger = get_logger("api_gateway.workspaces")

router = APIRouter()


def _get_workspace_or_raise(workspace_id: int) -> None:
    """Raise 403 if workspace does not exist. Step 200 isolation."""
    from amazon_research.db import get_workspace
    if get_workspace(workspace_id) is None:
        raise HTTPException(status_code=403, detail="invalid workspace_id")


@router.post("/{workspace_id}/opportunities/from-discovery")
def post_opportunity_from_discovery(
    workspace_id: int = Path(..., description="Workspace ID"),
    payload: Dict[str, Any] = Body(..., description="discovery_id?, keyword, market, category?, source_metadata?"),
) -> Dict[str, Any]:
    """Step 240: Convert discovery result to opportunity. Returns opportunity_id, status, message."""
    _get_workspace_or_raise(workspace_id)
    keyword = (payload.get("keyword") or "").strip() or None
    discovery_id = (payload.get("discovery_id") or "").strip() or None
    if not keyword and not discovery_id:
        raise HTTPException(status_code=400, detail="keyword or discovery_id required")
    try:
        from amazon_research.opportunity_conversion import convert_discovery_to_opportunity
        result = convert_discovery_to_opportunity(workspace_id, payload)
    except Exception as e:
        logger.warning("from-discovery conversion failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        raise HTTPException(status_code=500, detail="conversion_failed")
    return {"data": result, "meta": {"workspace_id": workspace_id}}


@router.post("/{workspace_id}/opportunities/compare")
def post_opportunities_compare(
    workspace_id: int = Path(..., description="Workspace ID"),
    payload: Dict[str, Any] = Body(..., description="opportunity_ids (max 5)"),
) -> Dict[str, Any]:
    """Steps 243–245: Compare up to 5 opportunities. Returns compared_items, score_comparison, risk_comparison, ranking_comparison."""
    _get_workspace_or_raise(workspace_id)
    ids = payload.get("opportunity_ids") or []
    if not isinstance(ids, list):
        ids = []
    try:
        from amazon_research.research_intelligence import compare_opportunities
        result = compare_opportunities(workspace_id, ids)
    except Exception as e:
        logger.warning("opportunities compare failed workspace_id=%s: %s", workspace_id, e)
        raise HTTPException(status_code=500, detail="compare_failed")
    return {"data": result, "meta": {"workspace_id": workspace_id}}


@router.get("/{workspace_id}/opportunities/{opportunity_id}/timeline")
def get_opportunity_timeline_route(
    workspace_id: int = Path(..., description="Workspace ID"),
    opportunity_id: int = Path(..., description="Opportunity ID"),
) -> Dict[str, Any]:
    """Steps 246–248: Opportunity trend timeline. Uses persistence history (Step 236)."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_analytics import get_opportunity_timeline
        result = get_opportunity_timeline(workspace_id, opportunity_id)
    except Exception as e:
        logger.warning("opportunity timeline failed workspace_id=%s opportunity_id=%s: %s", workspace_id, opportunity_id, e)
        raise HTTPException(status_code=500, detail="timeline_unavailable")
    return {"data": result, "meta": {"workspace_id": workspace_id, "opportunity_id": opportunity_id}}


@router.get("/{workspace_id}/opportunities/{opportunity_id}")
def get_opportunity_detail(
    workspace_id: int = Path(..., description="Workspace ID"),
    opportunity_id: int = Path(..., description="Opportunity ID (opportunity_memory id)"),
) -> Dict[str, Any]:
    """Pipeline: Opportunity detail – id, title, score, priority, ranking_position, rationale_summary, recommended_action, risk_indicator, market, category, history."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_detail import get_opportunity_detail as get_detail
        detail = get_detail(workspace_id, opportunity_id)
    except Exception as e:
        logger.warning("opportunity detail failed workspace_id=%s opportunity_id=%s: %s", workspace_id, opportunity_id, e)
        raise HTTPException(status_code=500, detail="opportunity_detail_unavailable")
    if detail is None:
        raise HTTPException(status_code=404, detail="opportunity not found")
    return {"data": detail, "meta": {"workspace_id": workspace_id}}


@router.post("/{workspace_id}/opportunities/{opportunity_id}/watch")
def post_opportunity_watch(
    workspace_id: int = Path(..., description="Workspace ID"),
    opportunity_id: int = Path(..., description="Opportunity ID"),
) -> Dict[str, Any]:
    """Pipeline: Add opportunity to watchlist (portfolio). Prevents duplicates."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_detail import get_opportunity_detail, get_opportunity_ref_by_id
        from amazon_research.db import add_workspace_portfolio_item
        ref = get_opportunity_ref_by_id(workspace_id, opportunity_id)
        if not ref:
            raise HTTPException(status_code=404, detail="opportunity not found")
        detail = get_opportunity_detail(workspace_id, opportunity_id)
        title = (detail.get("title") or ref)[:200] if detail else ref[:200]
        out = add_workspace_portfolio_item(workspace_id, "opportunity", ref, item_label=title, source_type="watch")
        return {"data": {"watched": True, "portfolio_id": out.get("id"), "created": out.get("created", False)}, "meta": {"workspace_id": workspace_id}}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("opportunity watch failed workspace_id=%s opportunity_id=%s: %s", workspace_id, opportunity_id, e)
        raise HTTPException(status_code=500, detail="watch_failed")


@router.delete("/{workspace_id}/opportunities/{opportunity_id}/watch")
def delete_opportunity_watch(
    workspace_id: int = Path(..., description="Workspace ID"),
    opportunity_id: int = Path(..., description="Opportunity ID"),
) -> Dict[str, Any]:
    """Pipeline: Remove opportunity from watchlist (archive portfolio item)."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_detail import get_opportunity_ref_by_id
        from amazon_research.db import get_workspace_portfolio_item_by_key, archive_workspace_portfolio_item
        ref = get_opportunity_ref_by_id(workspace_id, opportunity_id)
        if not ref:
            raise HTTPException(status_code=404, detail="opportunity not found")
        item = get_workspace_portfolio_item_by_key(workspace_id, "opportunity", ref)
        if not item or not item.get("id"):
            return {"data": {"watched": False, "removed": False}, "meta": {"workspace_id": workspace_id}}
        archived = archive_workspace_portfolio_item(workspace_id, item["id"])
        return {"data": {"watched": False, "removed": archived}, "meta": {"workspace_id": workspace_id}}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("opportunity unwatch failed workspace_id=%s opportunity_id=%s: %s", workspace_id, opportunity_id, e)
        raise HTTPException(status_code=500, detail="unwatch_failed")


@router.get("/{workspace_id}/opportunities/history")
def get_opportunities_history(
    workspace_id: int = Path(..., description="Workspace ID"),
    limit: int = Query(50, ge=1, le=200, description="Max history items"),
) -> Dict[str, Any]:
    """Step 236: Return recent opportunity feed history for workspace. Safe empty-state."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_persistence import get_opportunity_history_for_workspace
        items = get_opportunity_history_for_workspace(workspace_id, limit=limit)
    except Exception as e:
        logger.warning("opportunities history failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        raise HTTPException(status_code=500, detail="opportunities_history_unavailable")
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


@router.get("/{workspace_id}/opportunities")
def get_opportunities(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Return opportunity feed data (top opportunities) from dashboard serving layer. Stable fields for feed rendering."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.api import get_workspace_dashboard_response
        body = get_workspace_dashboard_response(workspace_id=workspace_id)
    except Exception as e:
        logger.warning("opportunities fetch failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        raise HTTPException(status_code=500, detail="opportunities_unavailable")
    if body.get("error"):
        raise HTTPException(status_code=403, detail=body.get("error", "opportunities_error"))
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    top_items = (data or {}).get("top_items") or {}
    items = top_items.get("top_opportunities") or []
    logger.info("opportunities served workspace_id=%s count=%s", workspace_id, len(items), extra={"workspace_id": workspace_id})
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


@router.get("/{workspace_id}/portfolio")
def get_portfolio(
    workspace_id: int = Path(..., description="Workspace ID"),
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    status: Optional[str] = Query(None, description="Filter by status (active, archived)"),
    limit: int = Query(500, ge=1, le=1000, description="Max items"),
) -> Dict[str, Any]:
    """Return workspace portfolio items list. Reuses existing API layer; safe empty-state."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.api import get_workspace_portfolio_response
        body = get_workspace_portfolio_response(workspace_id=workspace_id, item_type=item_type, status=status, limit=limit)
    except Exception as e:
        logger.warning("portfolio fetch failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        raise HTTPException(status_code=500, detail="portfolio_unavailable")
    if body.get("error"):
        raise HTTPException(status_code=403, detail=body.get("error", "portfolio_error"))
    return body


@router.get("/{workspace_id}/dashboard")
def get_dashboard(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Return workspace dashboard payload from existing dashboard serving layer (Step 211)."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.api import get_workspace_dashboard_response
        body = get_workspace_dashboard_response(workspace_id=workspace_id)
    except Exception as e:
        logger.warning("dashboard fetch failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        raise HTTPException(status_code=500, detail="dashboard_unavailable")
    if body.get("error"):
        raise HTTPException(status_code=403, detail=body.get("error", "dashboard_error"))
    logger.info("dashboard served workspace_id=%s", workspace_id, extra={"workspace_id": workspace_id})
    return body


@router.get("/{workspace_id}/portfolio/summary")
def get_portfolio_summary(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Return workspace portfolio summary. Reuses existing API layer."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.api import get_workspace_portfolio_summary_response
        body = get_workspace_portfolio_summary_response(workspace_id=workspace_id)
    except Exception as e:
        logger.warning("portfolio summary failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        raise HTTPException(status_code=500, detail="portfolio_unavailable")
    if body.get("error"):
        raise HTTPException(status_code=403, detail=body.get("error", "portfolio_error"))
    return body


@router.get("/{workspace_id}/alerts")
def get_alerts(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Return workspace alerts. Reuses existing API layer."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.api import get_workspace_alerts_response
        body = get_workspace_alerts_response(workspace_id=workspace_id, limit=100)
    except Exception as e:
        logger.warning("alerts fetch failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        raise HTTPException(status_code=500, detail="alerts_unavailable")
    if body.get("error"):
        raise HTTPException(status_code=403, detail=body.get("error", "alerts_error"))
    return body


@router.get("/{workspace_id}/strategy/summary")
def get_strategy_summary(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Return workspace strategy opportunities summary. Reuses existing API layer."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.api import get_workspace_strategy_opportunities_response
        body = get_workspace_strategy_opportunities_response(workspace_id=workspace_id)
    except Exception as e:
        logger.warning("strategy summary failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        raise HTTPException(status_code=500, detail="strategy_unavailable")
    if body.get("error"):
        raise HTTPException(status_code=403, detail=body.get("error", "strategy_error"))
    return body


# --- Steps 246–248: Saved searches ---
@router.get("/{workspace_id}/saved-searches")
def get_saved_searches(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Steps 246–248: List saved searches for workspace."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_analytics.saved_searches_service import list_saved_searches
        items = list_saved_searches(workspace_id)
    except Exception as e:
        logger.warning("saved-searches list failed workspace_id=%s: %s", workspace_id, e)
        raise HTTPException(status_code=500, detail="saved_searches_unavailable")
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


@router.post("/{workspace_id}/saved-searches")
def post_saved_search(
    workspace_id: int = Path(..., description="Workspace ID"),
    payload: Dict[str, Any] = Body(..., description="label, query?, market?, category?, limit?, sort?"),
) -> Dict[str, Any]:
    """Steps 246–248: Create a saved search."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_analytics.saved_searches_service import create_saved_search
        item = create_saved_search(
            workspace_id,
            label=payload.get("label") or "Saved search",
            query=payload.get("query"),
            market=payload.get("market"),
            category=payload.get("category"),
            limit=payload.get("limit", 50),
            sort=payload.get("sort", "recent"),
        )
    except Exception as e:
        logger.warning("saved-search create failed workspace_id=%s: %s", workspace_id, e)
        raise HTTPException(status_code=500, detail="create_failed")
    return {"data": item, "meta": {"workspace_id": workspace_id}}


@router.delete("/{workspace_id}/saved-searches/{search_id}")
def delete_saved_search(
    workspace_id: int = Path(..., description="Workspace ID"),
    search_id: int = Path(..., description="Saved search ID"),
) -> Dict[str, Any]:
    """Steps 246–248: Delete a saved search."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_analytics.saved_searches_service import delete_saved_search as do_delete
        removed = do_delete(workspace_id, search_id)
    except Exception as e:
        logger.warning("saved-search delete failed workspace_id=%s id=%s: %s", workspace_id, search_id, e)
        raise HTTPException(status_code=500, detail="delete_failed")
    return {"data": {"removed": removed}, "meta": {"workspace_id": workspace_id}}


# --- Steps 246–248: Discovery alert rules ---
@router.get("/{workspace_id}/discovery-alert-rules")
def get_discovery_alert_rules(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Steps 246–248: List discovery alert rules for workspace."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_analytics.discovery_alert_rules_service import list_discovery_alert_rules
        items = list_discovery_alert_rules(workspace_id)
    except Exception as e:
        logger.warning("discovery-alert-rules list failed workspace_id=%s: %s", workspace_id, e)
        raise HTTPException(status_code=500, detail="discovery_alert_rules_unavailable")
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


@router.post("/{workspace_id}/discovery-alert-rules")
def post_discovery_alert_rule(
    workspace_id: int = Path(..., description="Workspace ID"),
    payload: Dict[str, Any] = Body(..., description="keyword?, market?, category?, min_score?, min_opportunity_count?, enabled?"),
) -> Dict[str, Any]:
    """Steps 246–248: Create a discovery alert rule."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_analytics.discovery_alert_rules_service import create_discovery_alert_rule
        item = create_discovery_alert_rule(
            workspace_id,
            keyword=payload.get("keyword"),
            market=payload.get("market"),
            category=payload.get("category"),
            min_score=payload.get("min_score"),
            min_opportunity_count=payload.get("min_opportunity_count"),
            enabled=payload.get("enabled", True),
        )
    except Exception as e:
        logger.warning("discovery-alert-rule create failed workspace_id=%s: %s", workspace_id, e)
        raise HTTPException(status_code=500, detail="create_failed")
    return {"data": item, "meta": {"workspace_id": workspace_id}}


@router.delete("/{workspace_id}/discovery-alert-rules/{rule_id}")
def delete_discovery_alert_rule(
    workspace_id: int = Path(..., description="Workspace ID"),
    rule_id: int = Path(..., description="Rule ID"),
) -> Dict[str, Any]:
    """Steps 246–248: Delete a discovery alert rule."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.opportunity_analytics.discovery_alert_rules_service import delete_discovery_alert_rule as do_delete
        removed = do_delete(workspace_id, rule_id)
    except Exception as e:
        logger.warning("discovery-alert-rule delete failed workspace_id=%s id=%s: %s", workspace_id, rule_id, e)
        raise HTTPException(status_code=500, detail="delete_failed")
    return {"data": {"removed": removed}, "meta": {"workspace_id": workspace_id}}


# --- Steps 249–250: Research sessions ---
@router.get("/{workspace_id}/research-sessions")
def get_research_sessions(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Steps 249–250: List research sessions for workspace."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.research_workspace import list_research_sessions
        items = list_research_sessions(workspace_id)
    except Exception as e:
        logger.warning("research-sessions list failed workspace_id=%s: %s", workspace_id, e)
        raise HTTPException(status_code=500, detail="research_sessions_unavailable")
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


@router.post("/{workspace_id}/research-sessions")
def post_research_session(
    workspace_id: int = Path(..., description="Workspace ID"),
    payload: Dict[str, Any] = Body(..., description="label?, attached_searches?, attached_opportunities?, notes_summary?"),
) -> Dict[str, Any]:
    """Steps 249–250: Create a research session."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.research_workspace import create_research_session
        item = create_research_session(
            workspace_id,
            label=payload.get("label"),
            attached_searches=payload.get("attached_searches"),
            attached_opportunities=payload.get("attached_opportunities"),
            notes_summary=payload.get("notes_summary"),
        )
    except Exception as e:
        logger.warning("research-session create failed workspace_id=%s: %s", workspace_id, e)
        raise HTTPException(status_code=500, detail="create_failed")
    return {"data": item, "meta": {"workspace_id": workspace_id}}


@router.get("/{workspace_id}/research-sessions/{session_id}")
def get_research_session_by_id(
    workspace_id: int = Path(..., description="Workspace ID"),
    session_id: int = Path(..., description="Session ID"),
) -> Dict[str, Any]:
    """Steps 249–250: Get one research session by id."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.research_workspace import get_research_session
        session = get_research_session(workspace_id, session_id)
    except Exception as e:
        logger.warning("research-session get failed workspace_id=%s session_id=%s: %s", workspace_id, session_id, e)
        raise HTTPException(status_code=500, detail="session_unavailable")
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {"data": session, "meta": {"workspace_id": workspace_id}}


# --- Steps 249–250: Research performance metrics ---
@router.get("/{workspace_id}/research/metrics")
def get_research_metrics_route(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Steps 249–250: Research performance metrics for workspace."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.research_workspace import get_research_metrics
        metrics = get_research_metrics(workspace_id)
    except Exception as e:
        logger.warning("research metrics failed workspace_id=%s: %s", workspace_id, e)
        raise HTTPException(status_code=500, detail="metrics_unavailable")
    return {"data": metrics, "meta": {"workspace_id": workspace_id}}
