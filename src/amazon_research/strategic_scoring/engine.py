"""
Step 205: Strategic scoring layer – consolidate workspace decision signals into normalized strategic scores.
Deterministic, rule-based; consumes strategy, market entry, risk detection, workspace intelligence.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("strategic_scoring.engine")

BAND_STRONG = "strong"
BAND_MODERATE = "moderate"
BAND_WEAK = "weak"

# Score bands (tunable)
STRONG_MIN = 70
MODERATE_MIN = 40
# weak: score < 40

# Base scores by strategy/market status
SCORE_ACT_NOW = 80
SCORE_MONITOR = 55
SCORE_DEPRIORITIZE = 25
SCORE_ENTER_NOW = 78
SCORE_MARKET_MONITOR = 50
SCORE_DEFER = 22

# Risk adjustment: subtract from strategic_score
RISK_PENALTY_HIGH = 15
RISK_PENALTY_MEDIUM = 8
TOP_SCORED_LIMIT = 20


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _score_to_band(score: float) -> str:
    if score >= STRONG_MIN:
        return BAND_STRONG
    if score >= MODERATE_MIN:
        return BAND_MODERATE
    return BAND_WEAK


def _clamp_score(score: float) -> float:
    return max(0.0, min(100.0, round(score, 1)))


def _build_scored_item(
    item_type: str,
    item_key: str,
    item_label: str,
    strategic_score: float,
    strategic_band: str,
    rationale: str,
    supporting_signals: Dict[str, Any],
    recommended_action: str,
    risk_adjustment_notes: List[str],
) -> Dict[str, Any]:
    return {
        "item_type": item_type,
        "item_key": item_key,
        "item_label": item_label or item_key,
        "strategic_score": strategic_score,
        "strategic_band": strategic_band,
        "rationale": rationale,
        "supporting_signals": supporting_signals or {},
        "recommended_action": recommended_action,
        "risk_adjustment_notes": risk_adjustment_notes or [],
    }


def generate_workspace_strategic_scores(workspace_id: Optional[int]) -> Dict[str, Any]:
    """
    Produce normalized strategic scoring output for a workspace.
    Consumes opportunity strategy, market entry signals, risk detection, workspace intelligence.
    Aggregates into scored_items with strategic_score and strategic_band; risk adjusts scores.
    Stable shape; empty lists when data missing. Never raises.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "generated_at": _now_utc().isoformat(),
        "scored_items": [],
        "top_scored_items": [],
        "score_summary": {},
        "rationale_summary": {},
        "top_strategic_actions": [],
        "risk_adjustment_notes": [],
        "confidence_indicators": {},
    }
    if workspace_id is None:
        logger.warning("strategic_scoring generation skipped workspace_id=None")
        return out

    logger.info("strategic_scoring generation start workspace_id=%s", workspace_id)
    strategy: Dict[str, Any] = {}
    market_entry: Dict[str, Any] = {}
    risk: Dict[str, Any] = {}
    intelligence: Dict[str, Any] = {}

    try:
        from amazon_research.opportunity_strategy import generate_workspace_opportunity_strategy
        strategy = generate_workspace_opportunity_strategy(workspace_id)
    except Exception as e:
        logger.warning("strategic_scoring strategy fetch failed workspace_id=%s: %s", workspace_id, e)
    try:
        from amazon_research.market_entry_signals import generate_workspace_market_entry_signals
        market_entry = generate_workspace_market_entry_signals(workspace_id)
    except Exception as e:
        logger.warning("strategic_scoring market_entry fetch failed workspace_id=%s: %s", workspace_id, e)
    try:
        from amazon_research.risk_detection import generate_workspace_risk_detection
        risk = generate_workspace_risk_detection(workspace_id)
    except Exception as e:
        logger.warning("strategic_scoring risk fetch failed workspace_id=%s: %s", workspace_id, e)
    try:
        from amazon_research.workspace_intelligence import get_workspace_intelligence_summary_prefer_cached
        intelligence = get_workspace_intelligence_summary_prefer_cached(workspace_id)
    except Exception as e:
        logger.warning("strategic_scoring intelligence fetch failed workspace_id=%s: %s", workspace_id, e)

    high_risk_count = len(risk.get("high_risk_items") or [])
    medium_risk_count = len(risk.get("medium_risk_items") or [])
    risk_penalty = high_risk_count * RISK_PENALTY_HIGH + medium_risk_count * RISK_PENALTY_MEDIUM
    risk_deduction = min(25, risk_penalty)
    global_risk_notes: List[str] = []
    if high_risk_count > 0:
        global_risk_notes.append(f"{high_risk_count} high-risk item(s) reduce strategic score.")
    if medium_risk_count > 0:
        global_risk_notes.append(f"{medium_risk_count} medium-risk item(s) applied.")

    scored_items: List[Dict[str, Any]] = []

    # --- Opportunity-level items from strategy
    for lst, base_score in (
        (strategy.get("prioritized_opportunities") or [], SCORE_ACT_NOW),
        (strategy.get("monitor_opportunities") or [], SCORE_MONITOR),
        (strategy.get("deprioritized_opportunities") or [], SCORE_DEPRIORITIZE),
    ):
        for opp in lst:
            ref = (opp.get("opportunity_id") or "").strip()
            if not ref:
                continue
            raw = _safe_float(opp.get("opportunity_score"), base_score)
            score = _clamp_score(raw - risk_deduction)
            band = _score_to_band(score)
            risk_notes = list(global_risk_notes) if risk_deduction > 0 else []
            scored_items.append(_build_scored_item(
                item_type="opportunity",
                item_key=ref,
                item_label=ref,
                strategic_score=round(score, 1),
                strategic_band=band,
                rationale=opp.get("rationale") or f"Strategy signal; base score {raw:.1f}, band {band}.",
                supporting_signals=opp.get("supporting_signals") or {},
                recommended_action=opp.get("recommended_action") or "Review and act per strategy.",
                risk_adjustment_notes=risk_notes,
            ))

    # --- Market-level items from market entry signals
    for sig in market_entry.get("market_signals") or []:
        market_key = (sig.get("market_key") or "").strip()
        if not market_key:
            continue
        status = (sig.get("recommendation_status") or "").strip()
        if status == "enter_now":
            base = SCORE_ENTER_NOW
        elif status == "monitor_market":
            base = SCORE_MARKET_MONITOR
        else:
            base = SCORE_DEFER
        score = _clamp_score(base - risk_deduction)
        band = _score_to_band(score)
        risk_notes = list(global_risk_notes) if risk_deduction > 0 else []
        scored_items.append(_build_scored_item(
            item_type="market",
            item_key=market_key,
            item_label=f"Market {market_key}",
            strategic_score=round(score, 1),
            strategic_band=band,
            rationale=sig.get("rationale") or f"Market entry signal: {status}; band {band}.",
            supporting_signals=sig.get("supporting_signals") or {},
            recommended_action=sig.get("recommended_action") or "Review market entry strategy.",
            risk_adjustment_notes=risk_notes,
        ))

    # --- Workspace-level composite item
    total_opps = intelligence.get("total_tracked_opportunities")
    total_opps = int(total_opps) if total_opps is not None else 0
    avg_score = _safe_float(intelligence.get("average_opportunity_score"), 50.0)
    composite = (avg_score * 0.5 + (min(100, total_opps * 2) * 0.5)) if total_opps else avg_score
    composite = _clamp_score(composite - risk_deduction)
    band = _score_to_band(composite)
    scored_items.append(_build_scored_item(
        item_type="workspace",
        item_key=f"workspace_{workspace_id}",
        item_label=f"Workspace {workspace_id}",
        strategic_score=round(composite, 1),
        strategic_band=band,
        rationale=f"Composite from opportunity mix and risk; {total_opps} opportunities, avg score {avg_score:.1f}.",
        supporting_signals={"total_tracked_opportunities": total_opps, "average_opportunity_score": avg_score, "risk_penalty_applied": risk_deduction},
        recommended_action="Address high risks and prioritize top_scored_items.",
        risk_adjustment_notes=global_risk_notes,
    ))

    # Sort by strategic_score descending; top_scored_items
    scored_items.sort(key=lambda x: _safe_float(x.get("strategic_score"), 0), reverse=True)
    top_scored = scored_items[:TOP_SCORED_LIMIT]

    out["scored_items"] = scored_items
    out["top_scored_items"] = top_scored
    out["score_summary"] = {
        "total_items": len(scored_items),
        "strong_count": sum(1 for s in scored_items if s.get("strategic_band") == BAND_STRONG),
        "moderate_count": sum(1 for s in scored_items if s.get("strategic_band") == BAND_MODERATE),
        "weak_count": sum(1 for s in scored_items if s.get("strategic_band") == BAND_WEAK),
        "risk_penalty_applied": risk_deduction,
    }
    out["rationale_summary"] = {
        "message": f"Consolidated {len(scored_items)} items; risk penalty {risk_deduction} applied where relevant.",
    }
    out["top_strategic_actions"] = [
        "Prioritize items in top_scored_items with strong band.",
        "Review moderate-band items for improvement or risk mitigation.",
        "Address risk_adjustment_notes to improve overall strategic score.",
    ][:5]
    out["risk_adjustment_notes"] = global_risk_notes
    out["confidence_indicators"] = {
        "strategy_used": bool(strategy.get("prioritized_opportunities") is not None),
        "market_entry_used": bool(market_entry.get("market_signals") is not None),
        "risk_used": bool(risk.get("risk_items") is not None),
        "intelligence_used": bool(intelligence.get("total_tracked_opportunities") is not None),
        "scored_item_count": len(scored_items),
    }

    logger.info(
        "strategic_scoring generation success workspace_id=%s items=%s strong=%s moderate=%s weak=%s",
        workspace_id,
        len(scored_items),
        out["score_summary"].get("strong_count", 0),
        out["score_summary"].get("moderate_count", 0),
        out["score_summary"].get("weak_count", 0),
    )
    return out
