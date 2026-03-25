"""
Step 211: Dashboard data aggregation – workspace-scoped payload from intelligence, strategy, portfolio, risk, market, activity.
Stable shape; graceful fallback per section; no hot recomputation loops.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("dashboard_serving.aggregation")

TOP_ITEMS_LIMIT = 5
TOP_ACTIONS_LIMIT = 10
RECENT_ACTIVITY_LIMIT = 10


def _safe_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _default_overview(workspace_id: Optional[int]) -> Dict[str, Any]:
    return {
        "total_opportunities": 0,
        "high_priority_opportunities": 0,
        "total_portfolio_items": 0,
        "high_risk_item_count": 0,
        "top_strategic_score_count": 0,
        "last_updated": None,
    }


def _default_top_items() -> Dict[str, Any]:
    return {
        "top_opportunities": [],
        "top_recommendations": [],
        "top_risks": [],
        "top_markets": [],
    }


def get_dashboard_payload(workspace_id: Optional[int]) -> Dict[str, Any]:
    """
    Aggregate workspace-scoped backend outputs into a stable dashboard payload.
    Uses cached/preferred reads where available; degrades gracefully per section.
    Never raises.
    """
    if workspace_id is None:
        return _minimal_payload(workspace_id, "workspace_id required")

    logger.info("dashboard_serving aggregation start workspace_id=%s", workspace_id, extra={"workspace_id": workspace_id})

    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": _default_overview(workspace_id),
        "intelligence_summary": {},
        "strategy_summary": {},
        "portfolio_summary": {},
        "risk_summary": {},
        "market_summary": {},
        "activity_summary": {},
        "top_items": _default_top_items(),
        "top_actions": [],
        "notices": [],
        "health_indicators": {},
    }

    # Intelligence (prefer cached)
    try:
        from amazon_research.workspace_intelligence import get_workspace_intelligence_summary_prefer_cached
        data = get_workspace_intelligence_summary_prefer_cached(workspace_id)
        if isinstance(data, dict):
            out["intelligence_summary"] = data
            out["overview"]["total_opportunities"] = _safe_int(data.get("total_tracked_opportunities"))
            out["overview"]["high_priority_opportunities"] = _safe_int(data.get("active_high_priority_count"))
            out["overview"]["last_updated"] = data.get("summary_timestamp")
    except Exception as e:
        logger.warning("dashboard_serving upstream section fallback used intelligence workspace_id=%s: %s", workspace_id, e)
        out["health_indicators"]["intelligence"] = "fallback"

    # Portfolio summary
    try:
        from amazon_research.db.workspace_portfolio import get_workspace_portfolio_summary
        data = get_workspace_portfolio_summary(workspace_id)
        if isinstance(data, dict):
            out["portfolio_summary"] = data
            out["overview"]["total_portfolio_items"] = _safe_int(data.get("total"))
    except Exception as e:
        logger.warning("dashboard_serving upstream section fallback used portfolio workspace_id=%s: %s", workspace_id, e)
        out["health_indicators"]["portfolio"] = "fallback"

    # Activity summary and recent activity
    try:
        from amazon_research.db.workspace_activity_log import get_workspace_activity_summary, list_workspace_activity_events
        summary = get_workspace_activity_summary(workspace_id)
        if isinstance(summary, dict):
            out["activity_summary"] = summary
        events = list_workspace_activity_events(workspace_id, limit=RECENT_ACTIVITY_LIMIT)
        if events and "recent_events" not in out["activity_summary"]:
            out["activity_summary"] = dict(out["activity_summary"])
            out["activity_summary"]["recent_events"] = events[:RECENT_ACTIVITY_LIMIT]
    except Exception as e:
        logger.warning("dashboard_serving upstream section fallback used activity workspace_id=%s: %s", workspace_id, e)
        out["health_indicators"]["activity"] = "fallback"

    # Strategy
    try:
        from amazon_research.opportunity_strategy import generate_workspace_opportunity_strategy
        data = generate_workspace_opportunity_strategy(workspace_id)
        if isinstance(data, dict):
            out["strategy_summary"] = {
                "generated_at": data.get("generated_at"),
                "strategy_summary": data.get("strategy_summary"),
                "act_now_count": _safe_int((data.get("strategy_summary") or {}).get("act_now_count")),
            }
            pri = data.get("prioritized_opportunities") or []
            for opp in pri[:TOP_ITEMS_LIMIT]:
                supporting = opp.get("supporting_signals") or {}
                out["top_items"]["top_opportunities"].append({
                    "opportunity_id": opp.get("opportunity_id"),
                    "strategy_status": opp.get("strategy_status"),
                    "priority_level": opp.get("priority_level"),
                    "opportunity_score": supporting.get("opportunity_score"),
                    "rationale": (opp.get("rationale") or "")[:200],
                    "recommended_action": opp.get("recommended_action"),
                    "risk_notes": opp.get("risk_notes") or [],
                })
            out["top_actions"].extend((data.get("top_actions") or [])[:3])
            out["notices"].extend((data.get("risk_flags") or [])[:3])
    except Exception as e:
        logger.warning("dashboard_serving upstream section fallback used strategy workspace_id=%s: %s", workspace_id, e)
        out["health_indicators"]["strategy"] = "fallback"

    # Step 234: Real opportunity feed – prefer real pipeline data for top_opportunities when available
    try:
        from amazon_research.opportunity_feed import get_opportunity_feed_for_dashboard
        real_feed = get_opportunity_feed_for_dashboard(workspace_id, limit=TOP_ITEMS_LIMIT * 4)
        if real_feed:
            out["top_items"]["top_opportunities"] = real_feed[:TOP_ITEMS_LIMIT]
    except Exception as e:
        logger.warning("dashboard_serving real opportunity feed fallback workspace_id=%s: %s", workspace_id, e)

    # Portfolio recommendations
    try:
        from amazon_research.portfolio_recommendations import generate_workspace_portfolio_recommendations
        data = generate_workspace_portfolio_recommendations(workspace_id)
        if isinstance(data, dict):
            add_recs = data.get("add_recommendations") or []
            for r in add_recs[:TOP_ITEMS_LIMIT]:
                out["top_items"]["top_recommendations"].append({
                    "item_key": r.get("item_key"),
                    "priority_level": r.get("priority_level"),
                    "rationale": (r.get("rationale") or "")[:200],
                })
            out["top_actions"].extend((data.get("top_portfolio_actions") or [])[:2])
    except Exception as e:
        logger.warning("dashboard_serving upstream section fallback used recommendations workspace_id=%s: %s", workspace_id, e)
        out["health_indicators"]["recommendations"] = "fallback"

    # Market entry
    try:
        from amazon_research.market_entry_signals import generate_workspace_market_entry_signals
        data = generate_workspace_market_entry_signals(workspace_id)
        if isinstance(data, dict):
            out["market_summary"] = {
                "generated_at": data.get("generated_at"),
                "market_entry_summary": data.get("market_entry_summary"),
            }
            signals = data.get("market_signals") or []
            enter_now = [s for s in signals if (s.get("recommendation_status") or "").strip() == "enter_now"]
            for s in (enter_now or signals)[:TOP_ITEMS_LIMIT]:
                out["top_items"]["top_markets"].append({
                    "market_key": s.get("market_key"),
                    "recommendation_status": s.get("recommendation_status"),
                    "rationale": (s.get("rationale") or "")[:200],
                })
            out["top_actions"].extend((data.get("top_market_actions") or [])[:2])
            out["notices"].extend((data.get("risk_flags") or [])[:2])
    except Exception as e:
        logger.warning("dashboard_serving upstream section fallback used market workspace_id=%s: %s", workspace_id, e)
        out["health_indicators"]["market"] = "fallback"

    # Risk detection
    try:
        from amazon_research.risk_detection import generate_workspace_risk_detection
        data = generate_workspace_risk_detection(workspace_id)
        if isinstance(data, dict):
            out["risk_summary"] = {
                "generated_at": data.get("generated_at"),
                "risk_summary": data.get("risk_summary"),
                "high_risk_count": len(data.get("high_risk_items") or []),
            }
            out["overview"]["high_risk_item_count"] = len(data.get("high_risk_items") or [])
            high = data.get("high_risk_items") or []
            for r in high[:TOP_ITEMS_LIMIT]:
                out["top_items"]["top_risks"].append({
                    "item_key": r.get("item_key"),
                    "risk_type": r.get("risk_type"),
                    "risk_level": r.get("risk_level"),
                    "rationale": (r.get("rationale") or "")[:200],
                })
            out["top_actions"].extend((data.get("top_risk_actions") or [])[:2])
            out["notices"].extend((data.get("mitigation_suggestions") or [])[:2])
    except Exception as e:
        logger.warning("dashboard_serving upstream section fallback used risk workspace_id=%s: %s", workspace_id, e)
        out["health_indicators"]["risk"] = "fallback"

    # Strategic scoring
    try:
        from amazon_research.strategic_scoring import generate_workspace_strategic_scores
        data = generate_workspace_strategic_scores(workspace_id)
        if isinstance(data, dict):
            top = data.get("top_scored_items") or []
            out["overview"]["top_strategic_score_count"] = len(top)
            out["top_actions"].extend((data.get("top_strategic_actions") or [])[:2])
    except Exception as e:
        logger.warning("dashboard_serving upstream section fallback used strategic_scoring workspace_id=%s: %s", workspace_id, e)
        out["health_indicators"]["strategic_scoring"] = "fallback"

    out["top_actions"] = list(dict.fromkeys(out["top_actions"]))[:TOP_ACTIONS_LIMIT]
    out["notices"] = out["notices"][:10]
    if not out["health_indicators"]:
        out["health_indicators"] = {"status": "ok"}

    # Step 221: Demo data mode – substitute full demo payload when workspace is empty or DEMO_MODE_ENABLED
    # Step 225: Respect feature flag demo_mode
    try:
        from amazon_research.feature_flags import is_feature_enabled
        if is_feature_enabled("demo_mode"):
            from amazon_research.demo_data import should_use_demo_for_dashboard, generate_demo_dashboard_payload
            if should_use_demo_for_dashboard(workspace_id, out):
                demo = generate_demo_dashboard_payload(workspace_id)
                logger.info("dashboard_serving demo payload served workspace_id=%s", workspace_id, extra={"workspace_id": workspace_id})
                return demo
    except Exception as e:
        logger.warning("dashboard_serving demo check skipped workspace_id=%s: %s", workspace_id, e)

    logger.info(
        "dashboard_serving aggregation success workspace_id=%s overview_keys=%s",
        workspace_id, list(out["overview"].keys()),
        extra={"workspace_id": workspace_id},
    )
    return out


def _minimal_payload(workspace_id: Optional[int], reason: str = "") -> Dict[str, Any]:
    return {
        "workspace_id": workspace_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": _default_overview(workspace_id),
        "intelligence_summary": {},
        "strategy_summary": {},
        "portfolio_summary": {},
        "risk_summary": {},
        "market_summary": {},
        "activity_summary": {},
        "top_items": _default_top_items(),
        "top_actions": [],
        "notices": [reason] if reason else [],
        "health_indicators": {"status": "degraded", "reason": reason or "unknown"},
    }
