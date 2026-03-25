"""
Step 178: Strategic opportunity recommendations – recommendation engine for opportunities.
Types: focus_opportunity, watch_opportunity, diversify_portfolio, reduce_risk, exit_declining_opportunity.
Uses lifecycle engine, risk/reward map, portfolio tracker, portfolio strategy insights, predictive watch, anomaly alerts.
Integrates with workspace feed, copilot strategy advisor, portfolio strategy insights, dashboards.
Rule-based, explainable. Does not modify crawler, worker, auth, billing, UI.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.strategic_opportunity_recommendations")

# Recommendation types
RECO_FOCUS_OPPORTUNITY = "focus_opportunity"
RECO_WATCH_OPPORTUNITY = "watch_opportunity"
RECO_DIVERSIFY_PORTFOLIO = "diversify_portfolio"
RECO_REDUCE_RISK = "reduce_risk"
RECO_EXIT_DECLINING_OPPORTUNITY = "exit_declining_opportunity"

RECOMMENDATION_TYPES = [
    RECO_FOCUS_OPPORTUNITY,
    RECO_WATCH_OPPORTUNITY,
    RECO_DIVERSIFY_PORTFOLIO,
    RECO_REDUCE_RISK,
    RECO_EXIT_DECLINING_OPPORTUNITY,
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rec(
    workspace_id: int,
    recommendation_type: str,
    reasoning_summary: str,
    confidence: float,
    target_opportunity: Optional[str] = None,
    recommendation_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "workspace_id": workspace_id,
        "recommendation_id": recommendation_id or f"rec-{uuid.uuid4().hex[:12]}",
        "recommendation_type": recommendation_type,
        "target_opportunity": (target_opportunity or "").strip() or None,
        "reasoning_summary": (reasoning_summary or "").strip() or recommendation_type.replace("_", " "),
        "confidence": round(max(0.0, min(100.0, float(confidence))), 1),
        "timestamp": _now_iso(),
    }


def get_strategic_recommendations(
    workspace_id: int,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """
    Generate strategic opportunity recommendations from portfolio, risk/reward map, and strategy insights.
    Returns list of { workspace_id, recommendation_id, recommendation_type, target_opportunity, reasoning_summary, confidence, timestamp }.
    """
    results: List[Dict[str, Any]] = []
    seen_types_with_target: Set[tuple] = set()

    try:
        from amazon_research.discovery.opportunity_portfolio_tracker import get_workspace_portfolio, STATUS_RISING_CANDIDATE, STATUS_STRATEGIC_FOCUS, STATUS_DECLINING_ITEM
        from amazon_research.discovery.risk_reward_map import (
            get_workspace_risk_reward_map,
            QUADRANT_LOW_RISK_HIGH_REWARD,
            QUADRANT_HIGH_RISK_LOW_REWARD,
        )
        from amazon_research.discovery.portfolio_strategy_insights import get_portfolio_strategy_insights
    except ImportError as e:
        logger.debug("get_strategic_recommendations import: %s", e)
        return results

    portfolio = get_workspace_portfolio(workspace_id, limit=limit * 2)
    portfolio_by_ref: Dict[str, Dict[str, Any]] = {}
    for it in portfolio:
        ref = ((it.get("target_entity") or {}).get("ref") or "").strip()
        if ref:
            portfolio_by_ref[ref] = it

    risk_reward_list = get_workspace_risk_reward_map(workspace_id, limit=limit * 2)
    insights = get_portfolio_strategy_insights(workspace_id, portfolio=portfolio, portfolio_limit=limit * 2)
    suggested_actions = insights.get("suggested_portfolio_actions") or []
    weaknesses = insights.get("weaknesses") or []
    metrics = insights.get("metrics") or {}

    # 1) focus_opportunity: low_risk_high_reward not already strategic_focus
    for rr in risk_reward_list:
        ref = (rr.get("opportunity_id") or "").strip()
        if not ref:
            continue
        quad = rr.get("quadrant_classification") or ""
        port_item = portfolio_by_ref.get(ref)
        status = (port_item or {}).get("portfolio_status") or ""
        if quad == QUADRANT_LOW_RISK_HIGH_REWARD and status != STATUS_STRATEGIC_FOCUS:
            key = (RECO_FOCUS_OPPORTUNITY, ref)
            if key not in seen_types_with_target:
                seen_types_with_target.add(key)
                reward = rr.get("reward_score") or 50
                results.append(_rec(
                    workspace_id,
                    RECO_FOCUS_OPPORTUNITY,
                    f"Low risk, high reward (reward score {reward}); consider adding to strategic focus.",
                    min(90, 60 + (reward or 0) / 4),
                    target_opportunity=ref,
                ))

    # 2) watch_opportunity: rising_candidate or early_watch from portfolio
    for ref, it in portfolio_by_ref.items():
        status = it.get("portfolio_status") or ""
        if status == STATUS_RISING_CANDIDATE:
            key = (RECO_WATCH_OPPORTUNITY, ref)
            if key not in seen_types_with_target:
                seen_types_with_target.add(key)
                results.append(_rec(
                    workspace_id,
                    RECO_WATCH_OPPORTUNITY,
                    "Rising candidate; maintain watch and monitor for entry.",
                    75.0,
                    target_opportunity=ref,
                ))

    # 3) diversify_portfolio: from strategy insights
    if any("diversif" in (a or "").lower() for a in suggested_actions):
        key = (RECO_DIVERSIFY_PORTFOLIO, "")
        if key not in seen_types_with_target:
            seen_types_with_target.add(key)
            results.append(_rec(
                workspace_id,
                RECO_DIVERSIFY_PORTFOLIO,
                "Portfolio is concentrated; consider adding strategic focus or rising candidates to diversify.",
                70.0,
                target_opportunity=None,
            ))

    # 4) reduce_risk: high risk in risk/reward or insights weakness
    if any("risk" in (w or "").lower() or "declining" in (w or "").lower() for w in weaknesses):
        for rr in risk_reward_list:
            ref = (rr.get("opportunity_id") or "").strip()
            if not ref:
                continue
            quad = rr.get("quadrant_classification") or ""
            risk = rr.get("risk_score") or 0
            if quad == QUADRANT_HIGH_RISK_LOW_REWARD or risk >= 70:
                key = (RECO_REDUCE_RISK, ref)
                if key not in seen_types_with_target:
                    seen_types_with_target.add(key)
                    results.append(_rec(
                        workspace_id,
                        RECO_REDUCE_RISK,
                        f"High risk (score {risk}); consider reducing exposure or monitoring closely.",
                        min(85, 50 + risk / 2),
                        target_opportunity=ref,
                    ))
                    if len([r for r in results if r.get("recommendation_type") == RECO_REDUCE_RISK]) >= 5:
                        break

    # 5) exit_declining_opportunity: declining_item in portfolio
    for ref, it in portfolio_by_ref.items():
        status = it.get("portfolio_status") or ""
        if status == STATUS_DECLINING_ITEM:
            key = (RECO_EXIT_DECLINING_OPPORTUNITY, ref)
            if key not in seen_types_with_target:
                seen_types_with_target.add(key)
                results.append(_rec(
                    workspace_id,
                    RECO_EXIT_DECLINING_OPPORTUNITY,
                    "Opportunity is declining or fading; consider exiting or deprioritizing.",
                    80.0,
                    target_opportunity=ref,
                ))

    # Sort: focus first, then watch, then diversify, reduce_risk, exit last
    order = {RECO_FOCUS_OPPORTUNITY: 0, RECO_WATCH_OPPORTUNITY: 1, RECO_DIVERSIFY_PORTFOLIO: 2, RECO_REDUCE_RISK: 3, RECO_EXIT_DECLINING_OPPORTUNITY: 4}
    results.sort(key=lambda r: (order.get(r.get("recommendation_type"), 99), -(r.get("confidence") or 0)))
    return results[:limit]


def to_feed_item(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """Convert one recommendation to workspace opportunity feed item shape."""
    return {
        "workspace_id": recommendation.get("workspace_id"),
        "feed_item_type": "strategic_recommendation",
        "target_entity": {"ref": recommendation.get("target_opportunity"), "type": "opportunity"},
        "priority_score": recommendation.get("confidence") or 50,
        "short_explanation": recommendation.get("reasoning_summary") or "",
        "timestamp": recommendation.get("timestamp"),
        "recommendation_type": recommendation.get("recommendation_type"),
        "recommendation_id": recommendation.get("recommendation_id"),
    }
