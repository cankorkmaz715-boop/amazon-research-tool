"""
Step 204: Risk detection engine – workspace-scoped risk identification and classification.
Deterministic, rule-based; consumes workspace intelligence, strategy, portfolio recommendations, market entry signals.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("risk_detection.engine")

RISK_HIGH = "high"
RISK_MEDIUM = "medium"
RISK_LOW = "low"

# Risk types (v1)
RISK_COMPETITION = "competition_risk"
RISK_SATURATION = "saturation_risk"
RISK_TREND_INSTABILITY = "trend_instability_risk"
RISK_PORTFOLIO_CONCENTRATION = "portfolio_concentration_risk"
RISK_MARKET_ENTRY = "market_entry_risk"
RISK_ALERT_PATTERN = "alert_pattern_risk"
RISK_LOW_CONFIDENCE = "low_confidence_signal_risk"

# Rule thresholds
ALERT_COUNT_HIGH_RISK = 20
ALERT_COUNT_MEDIUM_RISK = 5
DEPRIORITIZED_RATIO_SATURATION = 0.6
ARCHIVE_COUNT_PORTFOLIO_RISK = 5
MIN_OPPORTUNITIES_LOW_CONFIDENCE = 3


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _build_risk_item(
    item_type: str,
    item_key: str,
    risk_type: str,
    risk_level: str,
    rationale: str,
    supporting_signals: Dict[str, Any],
    recommended_action: str,
    mitigation_notes: List[str],
) -> Dict[str, Any]:
    return {
        "item_type": item_type,
        "item_key": item_key,
        "risk_type": risk_type,
        "risk_level": risk_level,
        "rationale": rationale,
        "supporting_signals": supporting_signals or {},
        "recommended_action": recommended_action,
        "mitigation_notes": mitigation_notes or [],
    }


def generate_workspace_risk_detection(workspace_id: Optional[int]) -> Dict[str, Any]:
    """
    Produce normalized risk detection output for a workspace.
    Consumes workspace intelligence, opportunity strategy, portfolio recommendations, market entry signals.
    Stable shape; empty lists when data missing. Never raises.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "generated_at": _now_utc().isoformat(),
        "risk_items": [],
        "high_risk_items": [],
        "medium_risk_items": [],
        "low_risk_items": [],
        "risk_summary": {},
        "rationale_summary": {},
        "top_risk_actions": [],
        "mitigation_suggestions": [],
        "confidence_indicators": {},
    }
    if workspace_id is None:
        logger.warning("risk_detection generation skipped workspace_id=None")
        return out

    logger.info("risk_detection generation start workspace_id=%s", workspace_id)
    intelligence: Dict[str, Any] = {}
    strategy: Dict[str, Any] = {}
    portfolio_recs: Dict[str, Any] = {}
    market_entry: Dict[str, Any] = {}

    try:
        from amazon_research.workspace_intelligence import get_workspace_intelligence_summary_prefer_cached
        intelligence = get_workspace_intelligence_summary_prefer_cached(workspace_id)
    except Exception as e:
        logger.warning("risk_detection intelligence fetch failed workspace_id=%s: %s", workspace_id, e)
    try:
        from amazon_research.opportunity_strategy import generate_workspace_opportunity_strategy
        strategy = generate_workspace_opportunity_strategy(workspace_id)
    except Exception as e:
        logger.warning("risk_detection strategy fetch failed workspace_id=%s: %s", workspace_id, e)
    try:
        from amazon_research.portfolio_recommendations import generate_workspace_portfolio_recommendations
        portfolio_recs = generate_workspace_portfolio_recommendations(workspace_id)
    except Exception as e:
        logger.warning("risk_detection portfolio recommendations fetch failed workspace_id=%s: %s", workspace_id, e)
    try:
        from amazon_research.market_entry_signals import generate_workspace_market_entry_signals
        market_entry = generate_workspace_market_entry_signals(workspace_id)
    except Exception as e:
        logger.warning("risk_detection market entry fetch failed workspace_id=%s: %s", workspace_id, e)

    risk_items: List[Dict[str, Any]] = []
    total_opps = _safe_int(intelligence.get("total_tracked_opportunities"), 0)
    avg_score = _safe_float(intelligence.get("average_opportunity_score"), 0.0)
    alert_overview = intelligence.get("alert_overview") or {}
    alert_count = _safe_int(alert_overview.get("total_alerts") or alert_overview.get("count") or alert_overview.get("total") or 0, 0)

    # Alert pattern risk
    if alert_count >= ALERT_COUNT_HIGH_RISK:
        risk_items.append(_build_risk_item(
            item_type="workspace",
            item_key=f"workspace_{workspace_id}",
            risk_type=RISK_ALERT_PATTERN,
            risk_level=RISK_HIGH,
            rationale=f"High alert volume ({alert_count}); may indicate volatility or concentration of attention.",
            supporting_signals={"alert_count": alert_count, "threshold": ALERT_COUNT_HIGH_RISK},
            recommended_action="Review alert distribution and consider adjusting thresholds or diversifying focus.",
            mitigation_notes=["Tune alert preferences to reduce noise.", "Prioritize top opportunities only."],
        ))
    elif alert_count >= ALERT_COUNT_MEDIUM_RISK:
        risk_items.append(_build_risk_item(
            item_type="workspace",
            item_key=f"workspace_{workspace_id}",
            risk_type=RISK_ALERT_PATTERN,
            risk_level=RISK_MEDIUM,
            rationale=f"Elevated alert count ({alert_count}); monitor for pattern changes.",
            supporting_signals={"alert_count": alert_count},
            recommended_action="Monitor alert trends; consider refining filters.",
            mitigation_notes=[],
        ))

    # Saturation / competition risk from strategy (many deprioritized)
    pri_list = strategy.get("prioritized_opportunities") or []
    mon_list = strategy.get("monitor_opportunities") or []
    dep_list = strategy.get("deprioritized_opportunities") or []
    n_pri = len(pri_list)
    n_mon = len(mon_list)
    n_dep = len(dep_list)
    n_total_strat = n_pri + n_mon + n_dep
    if n_total_strat > 0 and n_dep / n_total_strat >= DEPRIORITIZED_RATIO_SATURATION:
        risk_items.append(_build_risk_item(
            item_type="opportunity_set",
            item_key=f"workspace_{workspace_id}",
            risk_type=RISK_SATURATION,
            risk_level=RISK_MEDIUM,
            rationale=f"Large share of opportunities deprioritized ({n_dep}/{n_total_strat}); possible saturation or strong competition.",
            supporting_signals={"deprioritized_count": n_dep, "total_strategy": n_total_strat, "ratio": round(n_dep / n_total_strat, 2)},
            recommended_action="Review deprioritized set; consider new niches or markets.",
            mitigation_notes=["Diversify opportunity sources.", "Revisit score thresholds."],
        ))
    if n_total_strat > 0 and avg_score < 45 and total_opps > 10:
        risk_items.append(_build_risk_item(
            item_type="opportunity_set",
            item_key=f"workspace_{workspace_id}",
            risk_type=RISK_COMPETITION,
            risk_level=RISK_LOW,
            rationale=f"Low average score ({avg_score:.1f}) with many opportunities; competition may be high.",
            supporting_signals={"average_score": avg_score, "total_opportunities": total_opps},
            recommended_action="Assess competition and differentiation; focus on higher-scoring segments.",
            mitigation_notes=[],
        ))

    # Portfolio concentration risk (many archive recommendations)
    archive_recs = portfolio_recs.get("archive_recommendations") or []
    if len(archive_recs) >= ARCHIVE_COUNT_PORTFOLIO_RISK:
        risk_items.append(_build_risk_item(
            item_type="portfolio",
            item_key=f"workspace_{workspace_id}",
            risk_type=RISK_PORTFOLIO_CONCENTRATION,
            risk_level=RISK_MEDIUM,
            rationale=f"Many items recommended for archive ({len(archive_recs)}); portfolio may be over-concentrated or stale.",
            supporting_signals={"archive_recommendation_count": len(archive_recs)},
            recommended_action="Review portfolio; archive low-value items and rebalance.",
            mitigation_notes=["Refresh portfolio with new opportunities from add_recommendations."],
        ))

    # Market entry risk (from market entry signals risk_flags or all defer)
    me_risk_flags = market_entry.get("risk_flags") or []
    rec_markets = market_entry.get("recommended_markets") or []
    defer_markets = market_entry.get("deprioritized_markets") or []
    if me_risk_flags or (len(rec_markets) == 0 and len(defer_markets) >= 2):
        risk_items.append(_build_risk_item(
            item_type="market",
            item_key="market_entry",
            risk_type=RISK_MARKET_ENTRY,
            risk_level=RISK_LOW if not me_risk_flags else RISK_MEDIUM,
            rationale="No strong market entry signals or market-entry risk flags present; expansion may be premature." if not me_risk_flags else "Market entry signals report risk flags; review before expanding.",
            supporting_signals={"risk_flags": me_risk_flags, "recommended_markets_count": len(rec_markets), "defer_markets_count": len(defer_markets)},
            recommended_action="Gather more data or improve signals before committing to new markets.",
            mitigation_notes=me_risk_flags[:3] if me_risk_flags else [],
        ))

    # Low confidence signal risk (sparse data)
    if total_opps < MIN_OPPORTUNITIES_LOW_CONFIDENCE and not risk_items:
        risk_items.append(_build_risk_item(
            item_type="workspace",
            item_key=f"workspace_{workspace_id}",
            risk_type=RISK_LOW_CONFIDENCE,
            risk_level=RISK_LOW,
            rationale=f"Few opportunities tracked ({total_opps}); risk view has limited signal.",
            supporting_signals={"total_tracked_opportunities": total_opps},
            recommended_action="Increase discovery or data coverage to improve risk assessment.",
            mitigation_notes=[],
        ))
    elif total_opps == 0:
        risk_items.append(_build_risk_item(
            item_type="workspace",
            item_key=f"workspace_{workspace_id}",
            risk_type=RISK_LOW_CONFIDENCE,
            risk_level=RISK_MEDIUM,
            rationale="No opportunities tracked; cannot assess opportunity-related risks.",
            supporting_signals={"total_tracked_opportunities": 0},
            recommended_action="Run discovery and ingestion to populate workspace data.",
            mitigation_notes=[],
        ))

    high_risk = [r for r in risk_items if r.get("risk_level") == RISK_HIGH]
    medium_risk = [r for r in risk_items if r.get("risk_level") == RISK_MEDIUM]
    low_risk = [r for r in risk_items if r.get("risk_level") == RISK_LOW]

    out["risk_items"] = risk_items
    out["high_risk_items"] = high_risk
    out["medium_risk_items"] = medium_risk
    out["low_risk_items"] = low_risk
    out["risk_summary"] = {
        "total_risk_items": len(risk_items),
        "high_count": len(high_risk),
        "medium_count": len(medium_risk),
        "low_count": len(low_risk),
    }
    out["rationale_summary"] = {
        "message": f"Identified {len(risk_items)} risk(s): {len(high_risk)} high, {len(medium_risk)} medium, {len(low_risk)} low.",
    }
    out["top_risk_actions"] = [
        "Address high_risk_items first.",
        "Review medium_risk_items and apply mitigations where appropriate.",
        "Monitor low_risk_items for changes.",
    ][:5]
    out["mitigation_suggestions"] = []
    for r in risk_items:
        for note in (r.get("mitigation_notes") or [])[:2]:
            if note and note not in out["mitigation_suggestions"]:
                out["mitigation_suggestions"].append(note)
    if not out["mitigation_suggestions"]:
        out["mitigation_suggestions"] = ["Review risk_items and apply recommended_action per item."]
    out["confidence_indicators"] = {
        "intelligence_used": bool(intelligence.get("total_tracked_opportunities") is not None),
        "strategy_used": bool(strategy.get("prioritized_opportunities") is not None),
        "portfolio_recs_used": bool(portfolio_recs.get("archive_recommendations") is not None),
        "market_entry_used": bool(market_entry.get("risk_flags") is not None),
        "risk_item_count": len(risk_items),
    }

    logger.info(
        "risk_detection generation success workspace_id=%s high=%s medium=%s low=%s",
        workspace_id,
        len(high_risk),
        len(medium_risk),
        len(low_risk),
    )
    return out
