"""
Step 176: Portfolio strategy insights – analyze portfolio characteristics on top of the opportunity portfolio tracker.
Concentration vs diversification, rising vs declining balance, niche/cluster focus, strategic focus stability, risk balance.
Integrates with opportunity portfolio tracker, workspace intelligence, copilot strategy advisor, workspace dashboards.
Lightweight, rule-based, explainable. Extensible for deeper portfolio analytics.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.portfolio_strategy_insights")

# Concentration thresholds (share of total items)
CONCENTRATION_THRESHOLD = 0.55   # >55% in one status = concentrated
DECLINING_RISK_THRESHOLD = 0.35  # >35% declining = risk
RISING_STRENGTH_THRESHOLD = 0.20 # >20% rising = strength
FOCUS_STABILITY_MIN = 2         # at least 2 strategic_focus for "stable focus"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _analyze_portfolio(portfolio: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute counts and shares by status and entity type. Rule-based metrics."""
    total = len(portfolio)
    by_status: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    for it in portfolio:
        s = it.get("portfolio_status") or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
        ent = (it.get("target_entity") or {}).get("type") or "opportunity"
        by_type[ent] = by_type.get(ent, 0) + 1
    shares = {k: (v / total if total else 0) for k, v in by_status.items()}
    return {
        "total_items": total,
        "by_status": by_status,
        "by_type": by_type,
        "shares_by_status": shares,
        "rising_count": by_status.get("rising_candidate", 0),
        "declining_count": by_status.get("declining_item", 0),
        "strategic_focus_count": by_status.get("strategic_focus", 0),
        "active_watch_count": by_status.get("active_watch", 0),
    }


def get_portfolio_strategy_insights(
    workspace_id: int,
    portfolio: Optional[List[Dict[str, Any]]] = None,
    portfolio_limit: int = 100,
) -> Dict[str, Any]:
    """
    Build portfolio strategy insights from tracker output. Returns:
    workspace_id, portfolio_insight_id, portfolio_health_summary, strategy_summary,
    strengths, weaknesses, suggested_portfolio_actions, timestamp.
    """
    insight_id = f"insight-{uuid.uuid4().hex[:12]}"
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "portfolio_insight_id": insight_id,
        "portfolio_health_summary": "",
        "strategy_summary": "",
        "strengths": [],
        "weaknesses": [],
        "suggested_portfolio_actions": [],
        "timestamp": _now_iso(),
    }

    if portfolio is None:
        try:
            from amazon_research.discovery.opportunity_portfolio_tracker import get_workspace_portfolio
            portfolio = get_workspace_portfolio(workspace_id, limit=portfolio_limit)
        except Exception as e:
            logger.debug("get_portfolio_strategy_insights get_workspace_portfolio: %s", e)
            portfolio = []

    total = len(portfolio)
    if total == 0:
        out["portfolio_health_summary"] = "Portfolio empty; add opportunities or watches to generate insights."
        out["strategy_summary"] = "No portfolio items to analyze."
        out["suggested_portfolio_actions"] = ["Add opportunities to watchlist or run discovery to populate portfolio."]
        return out

    metrics = _analyze_portfolio(portfolio)
    by_status = metrics["by_status"]
    shares = metrics["shares_by_status"]
    rising_count = metrics["rising_count"]
    declining_count = metrics["declining_count"]
    strategic_focus_count = metrics["strategic_focus_count"]

    # Concentration: max share in any single status
    max_share = max(shares.values()) if shares else 0
    is_concentrated = max_share >= CONCENTRATION_THRESHOLD
    dominant_status = max((k for k in by_status), key=lambda k: by_status.get(k, 0), default="")

    # Rising vs declining balance
    rising_share = rising_count / total if total else 0
    declining_share = declining_count / total if total else 0

    # Niche/cluster focus: share of cluster type or strategic_focus
    cluster_count = metrics["by_type"].get("cluster", 0) + strategic_focus_count
    focus_share = cluster_count / total if total else 0

    # Build health summary (short text)
    health_parts: List[str] = []
    if is_concentrated:
        health_parts.append(f"Concentrated in {dominant_status.replace('_', ' ')} ({max_share:.0%}).")
    else:
        health_parts.append("Portfolio is diversified across statuses.")
    health_parts.append(f"Rising: {rising_count}, declining: {declining_count}.")
    if strategic_focus_count >= FOCUS_STABILITY_MIN:
        health_parts.append(f"Strategic focus stable ({strategic_focus_count} items).")
    else:
        health_parts.append("Limited strategic focus items.")
    out["portfolio_health_summary"] = " ".join(health_parts)

    # Strategy summary
    strategy_parts: List[str] = []
    strategy_parts.append(f"Total items: {total}. Rising share: {rising_share:.0%}; declining share: {declining_share:.0%}.")
    if focus_share > 0:
        strategy_parts.append(f"Niche/cluster focus: {focus_share:.0%}.")
    out["strategy_summary"] = " ".join(strategy_parts)

    # Strengths
    strengths: List[str] = []
    if rising_share >= RISING_STRENGTH_THRESHOLD and rising_count > 0:
        strengths.append("Strong pipeline of rising candidates.")
    if not is_concentrated and total >= 3:
        strengths.append("Diversified portfolio across categories.")
    if strategic_focus_count >= FOCUS_STABILITY_MIN:
        strengths.append("Clear strategic focus areas.")
    if declining_share < 0.2 and declining_count <= 2:
        strengths.append("Low exposure to declining items.")
    out["strengths"] = strengths

    # Weaknesses
    weaknesses: List[str] = []
    if declining_share >= DECLINING_RISK_THRESHOLD:
        weaknesses.append("High share of declining or fading opportunities.")
    if is_concentrated and dominant_status == "declining_item":
        weaknesses.append("Portfolio concentrated in declining items.")
    if total > 0 and rising_count == 0 and strategic_focus_count == 0:
        weaknesses.append("No rising candidates or strategic focus; pipeline may need refresh.")
    if strategic_focus_count == 0 and total >= 5:
        weaknesses.append("No strategic focus items; consider defining focus niches.")
    out["weaknesses"] = weaknesses

    # Suggested actions (rule-based)
    actions: List[str] = []
    if declining_share >= DECLINING_RISK_THRESHOLD:
        actions.append("Review and consider reducing exposure to declining or fading items.")
    if rising_count == 0 and total > 0:
        actions.append("Run discovery or predictive watch to identify rising candidates.")
    if strategic_focus_count < FOCUS_STABILITY_MIN and total >= 3:
        actions.append("Add high-priority watches or align with workspace focus areas for strategic focus.")
    if is_concentrated and dominant_status == "active_watch":
        actions.append("Consider diversifying: add strategic focus or rising candidates.")
    if not actions:
        actions.append("Portfolio balance is reasonable; continue monitoring.")
    out["suggested_portfolio_actions"] = actions

    # Optional: pass through metrics for dashboards
    out["metrics"] = {
        "total_items": total,
        "concentration_ratio": round(max_share, 2),
        "rising_share": round(rising_share, 2),
        "declining_share": round(declining_share, 2),
        "strategic_focus_count": strategic_focus_count,
        "is_concentrated": is_concentrated,
    }

    return out


def get_insights_for_dashboard(workspace_id: int, limit: int = 100) -> Dict[str, Any]:
    """
    Return strategy insights in a form suitable for workspace dashboards.
    Same as get_portfolio_strategy_insights but name signals dashboard use.
    """
    return get_portfolio_strategy_insights(workspace_id, portfolio_limit=limit)
