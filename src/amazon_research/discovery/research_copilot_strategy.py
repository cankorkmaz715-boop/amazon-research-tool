"""
Step 179: Research copilot strategy layer – strategy-oriented copilot that interprets strategic recommendations in workspace context.
Uses: strategic opportunity recommendations, portfolio strategy insights, workspace intelligence, personalized copilot suggestions, risk/reward map.
Produces: strategy guidance (focus this niche, diversify portfolio, reduce exposure, watch emerging candidate, avoid unstable segment).
Rule-based, explainable, deterministic. Integrates with research dashboard, copilot strategy advisor, workspace feed, portfolio strategy insights.
No external AI. Extensible for future AI-powered strategic copilots.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.research_copilot_strategy")

# Guidance directions (recommended_strategic_direction)
DIRECTION_FOCUS_THIS_NICHE = "focus this niche"
DIRECTION_DIVERSIFY_PORTFOLIO = "diversify portfolio"
DIRECTION_REDUCE_EXPOSURE = "reduce exposure"
DIRECTION_WATCH_EMERGING_CANDIDATE = "watch emerging candidate"
DIRECTION_AVOID_UNSTABLE_SEGMENT = "avoid unstable segment"

DIRECTIONS = [
    DIRECTION_FOCUS_THIS_NICHE,
    DIRECTION_DIVERSIFY_PORTFOLIO,
    DIRECTION_REDUCE_EXPOSURE,
    DIRECTION_WATCH_EMERGING_CANDIDATE,
    DIRECTION_AVOID_UNSTABLE_SEGMENT,
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guidance(
    workspace_id: int,
    recommended_strategic_direction: str,
    reasoning_summary: str,
    main_supporting_signals: Dict[str, Any],
    strategy_guidance_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "workspace_id": workspace_id,
        "strategy_guidance_id": strategy_guidance_id or f"guidance-{uuid.uuid4().hex[:12]}",
        "recommended_strategic_direction": recommended_strategic_direction,
        "reasoning_summary": (reasoning_summary or "").strip() or recommended_strategic_direction,
        "main_supporting_signals": dict(main_supporting_signals or {}),
        "timestamp": _now_iso(),
    }


def get_copilot_strategy_guidance(
    workspace_id: int,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Build strategy guidance from strategic recommendations, portfolio insights, workspace intelligence,
    personalized suggestions, and risk/reward map. Returns list of guidance items with
    workspace_id, strategy_guidance_id, recommended_strategic_direction, reasoning_summary, main_supporting_signals, timestamp.
    """
    results: List[Dict[str, Any]] = []
    seen_direction: set = set()

    try:
        from amazon_research.discovery.strategic_opportunity_recommendations import (
            get_strategic_recommendations,
            RECO_FOCUS_OPPORTUNITY,
            RECO_WATCH_OPPORTUNITY,
            RECO_DIVERSIFY_PORTFOLIO,
            RECO_REDUCE_RISK,
            RECO_EXIT_DECLINING_OPPORTUNITY,
        )
        from amazon_research.discovery.portfolio_strategy_insights import get_portfolio_strategy_insights
        from amazon_research.discovery.risk_reward_map import get_workspace_risk_reward_map, QUADRANT_HIGH_RISK_LOW_REWARD
    except ImportError as e:
        logger.debug("get_copilot_strategy_guidance import: %s", e)
        return results

    recs = get_strategic_recommendations(workspace_id, limit=limit * 2)
    insights = get_portfolio_strategy_insights(workspace_id, portfolio_limit=limit * 2)
    risk_reward_list = get_workspace_risk_reward_map(workspace_id, limit=limit * 2)

    # Optional: workspace intelligence and personalized suggestions (for supporting signals)
    intel: Dict[str, Any] = {}
    suggestions: List[Dict[str, Any]] = []
    try:
        from amazon_research.monitoring import get_workspace_intelligence
        intel = get_workspace_intelligence(workspace_id)
    except Exception as e:
        logger.debug("get_copilot_strategy_guidance get_workspace_intelligence: %s", e)
    try:
        from amazon_research.discovery import get_personalized_suggestions
        suggestions = get_personalized_suggestions(workspace_id, limit=5)
    except Exception as e:
        logger.debug("get_copilot_strategy_guidance get_personalized_suggestions: %s", e)

    # Map recommendations to guidance directions (dedupe by direction)
    for r in recs:
        rec_type = r.get("recommendation_type") or ""
        target = r.get("target_opportunity") or ""
        reason = r.get("reasoning_summary") or ""
        conf = r.get("confidence") or 0
        if rec_type == RECO_FOCUS_OPPORTUNITY:
            direction = DIRECTION_FOCUS_THIS_NICHE
            if direction not in seen_direction:
                seen_direction.add(direction)
                results.append(_guidance(
                    workspace_id,
                    direction,
                    f"Strategic recommendation: focus high-potential opportunity. {reason}",
                    {"source": "strategic_recommendations", "recommendation_type": rec_type, "target_opportunity": target, "confidence": conf, "portfolio_insights": insights.get("portfolio_health_summary")},
                ))
        elif rec_type == RECO_WATCH_OPPORTUNITY:
            direction = DIRECTION_WATCH_EMERGING_CANDIDATE
            if direction not in seen_direction:
                seen_direction.add(direction)
                results.append(_guidance(
                    workspace_id,
                    direction,
                    f"Emerging or rising candidate worth watching. {reason}",
                    {"source": "strategic_recommendations", "recommendation_type": rec_type, "target_opportunity": target, "confidence": conf},
                ))
        elif rec_type == RECO_DIVERSIFY_PORTFOLIO:
            direction = DIRECTION_DIVERSIFY_PORTFOLIO
            if direction not in seen_direction:
                seen_direction.add(direction)
                results.append(_guidance(
                    workspace_id,
                    direction,
                    f"Portfolio concentration suggests diversifying. {reason}",
                    {"source": "strategic_recommendations", "recommendation_type": rec_type, "portfolio_insights": insights.get("suggested_portfolio_actions"), "strategy_summary": insights.get("strategy_summary")},
                ))
        elif rec_type in (RECO_REDUCE_RISK, RECO_EXIT_DECLINING_OPPORTUNITY):
            direction = DIRECTION_REDUCE_EXPOSURE
            if direction not in seen_direction:
                seen_direction.add(direction)
                results.append(_guidance(
                    workspace_id,
                    direction,
                    f"Risk or declining exposure suggests reducing exposure. {reason}",
                    {"source": "strategic_recommendations", "recommendation_type": rec_type, "target_opportunity": target, "confidence": conf, "weaknesses": insights.get("weaknesses")},
                ))

    # Avoid unstable segment: from risk/reward map (many high_risk_low_reward)
    high_risk_low_count = sum(1 for rr in risk_reward_list if (rr.get("quadrant_classification") or "") == QUADRANT_HIGH_RISK_LOW_REWARD)
    if high_risk_low_count >= 2 and DIRECTION_AVOID_UNSTABLE_SEGMENT not in seen_direction:
        seen_direction.add(DIRECTION_AVOID_UNSTABLE_SEGMENT)
        results.append(_guidance(
            workspace_id,
            DIRECTION_AVOID_UNSTABLE_SEGMENT,
            f"Multiple opportunities in high-risk, low-reward quadrant ({high_risk_low_count}); consider avoiding or reducing exposure to unstable segments.",
            {"source": "risk_reward_map", "high_risk_low_reward_count": high_risk_low_count, "portfolio_insights": insights.get("portfolio_health_summary")},
        ))

    # If no guidance yet, add a neutral summary from portfolio insights
    if not results and insights.get("portfolio_health_summary"):
        results.append(_guidance(
            workspace_id,
            DIRECTION_FOCUS_THIS_NICHE,
            "Portfolio summary: " + (insights.get("portfolio_health_summary") or ""),
            {"source": "portfolio_strategy_insights", "strategy_summary": insights.get("strategy_summary"), "workspace_intelligence": bool(intel), "suggestions_count": len(suggestions)},
        ))

    return results[:limit]


def get_strategy_guidance_for_dashboard(workspace_id: int, limit: int = 15) -> List[Dict[str, Any]]:
    """Return strategy guidance in a form suitable for research dashboard. Same as get_copilot_strategy_guidance with lower default limit."""
    return get_copilot_strategy_guidance(workspace_id, limit=limit)
