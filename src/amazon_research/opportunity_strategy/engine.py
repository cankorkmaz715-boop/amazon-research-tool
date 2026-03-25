"""
Step 201: Opportunity strategy engine – convert workspace opportunity data into structured strategic guidance.
Rule-based, deterministic; consumes rankings, intelligence summary, portfolio, alerts, alert preferences.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("opportunity_strategy.engine")

STRATEGY_ACT_NOW = "act_now"
STRATEGY_MONITOR = "monitor"
STRATEGY_DEPRIORITIZE = "deprioritize"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# Rule thresholds (tunable)
DEFAULT_ACT_NOW_SCORE_THRESHOLD = 70.0
DEFAULT_MONITOR_SCORE_THRESHOLD = 50.0


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _get_workspace_rankings(workspace_id: Optional[int], limit: int = 500) -> List[Dict[str, Any]]:
    """Rankings for refs that belong to this workspace. Returns [] on error."""
    if workspace_id is None:
        return []
    try:
        from amazon_research.db import list_opportunity_memory
        from amazon_research.db.opportunity_rankings import get_latest_rankings
        mem = list_opportunity_memory(limit=2000, workspace_id=workspace_id) or []
        refs = {m.get("opportunity_ref") for m in mem if m.get("opportunity_ref")}
        if not refs:
            return []
        all_rankings = get_latest_rankings(limit=5000)
        return [r for r in (all_rankings or []) if (r.get("opportunity_ref") or "") in refs][:limit]
    except Exception as e:
        logger.warning("opportunity_strategy workspace rankings failed workspace_id=%s: %s", workspace_id, e)
        return []


def _get_portfolio_refs(workspace_id: Optional[int]) -> set:
    """Set of item_key (and opportunity_ref-style keys) that are in workspace portfolio. Empty on error."""
    if workspace_id is None:
        return set()
    try:
        from amazon_research.db.workspace_portfolio import list_workspace_portfolio_items
        items = list_workspace_portfolio_items(workspace_id, status="active", limit=1000)
        refs = set()
        for it in items or []:
            key = (it.get("item_key") or "").strip()
            if key:
                refs.add(key)
            ref = (it.get("item_key") or "").strip()
            if ref and ":" not in ref and len(ref) == 10:
                refs.add(f"DE:{ref}")
        return refs
    except Exception as e:
        logger.warning("opportunity_strategy portfolio refs failed workspace_id=%s: %s", workspace_id, e)
        return set()


def _get_alert_refs(workspace_id: Optional[int]) -> set:
    """Set of target_entity (opportunity refs) that have recent alerts. Empty on error."""
    if workspace_id is None:
        return set()
    try:
        from amazon_research.db import list_opportunity_alerts
        rows = list_opportunity_alerts(limit=500, workspace_id=workspace_id) or []
        return {(r.get("target_entity") or "").strip() for r in rows if (r.get("target_entity") or "").strip()}
    except Exception as e:
        logger.warning("opportunity_strategy alert refs failed workspace_id=%s: %s", workspace_id, e)
        return set()


def _classify_opportunity(
    ref: str,
    score: float,
    in_portfolio: bool,
    has_alert: bool,
    act_now_threshold: float,
    monitor_threshold: float,
) -> tuple:
    """Returns (strategy_status, priority_level, rationale). Deterministic rule-based."""
    if score >= act_now_threshold and (has_alert or in_portfolio):
        return STRATEGY_ACT_NOW, PRIORITY_HIGH, "High score and alert or portfolio track; recommend immediate review."
    if score >= act_now_threshold:
        return STRATEGY_ACT_NOW, PRIORITY_HIGH, "Score above act-now threshold; consider adding to portfolio."
    if score >= monitor_threshold or in_portfolio:
        return STRATEGY_MONITOR, PRIORITY_MEDIUM, "Worth monitoring; score in range or already tracked."
    if has_alert:
        return STRATEGY_MONITOR, PRIORITY_MEDIUM, "Alert raised but score below threshold; monitor for changes."
    return STRATEGY_DEPRIORITIZE, PRIORITY_LOW, "Below monitor threshold; low priority unless signals improve."


def _build_opportunity_entry(
    ref: str,
    strategy_status: str,
    priority_level: str,
    rationale: str,
    score: float,
    in_portfolio: bool,
    has_alert: bool,
    supporting: Dict[str, Any],
) -> Dict[str, Any]:
    """Single classified opportunity entry for strategy output."""
    risk_notes: List[str] = []
    if supporting.get("competition_score") is not None and _safe_float(supporting.get("competition_score")) > 70:
        risk_notes.append("High competition score")
    recommended = "Review and decide" if strategy_status == STRATEGY_ACT_NOW else ("Monitor metrics" if strategy_status == STRATEGY_MONITOR else "No action unless signals change")
    return {
        "opportunity_id": ref,
        "strategy_status": strategy_status,
        "priority_level": priority_level,
        "rationale": rationale,
        "supporting_signals": supporting,
        "recommended_action": recommended,
        "risk_notes": risk_notes if risk_notes else [],
    }


def generate_workspace_opportunity_strategy(
    workspace_id: Optional[int],
    act_now_threshold: Optional[float] = None,
    monitor_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Produce normalized strategy output for a workspace. Consumes rankings, intelligence, portfolio, alerts.
    Returns stable shape; empty lists and safe defaults when data missing. Never raises.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "generated_at": _now_utc().isoformat(),
        "prioritized_opportunities": [],
        "monitor_opportunities": [],
        "deprioritized_opportunities": [],
        "strategy_summary": {},
        "rationale_summary": {},
        "top_actions": [],
        "risk_flags": [],
        "confidence_indicators": {},
    }
    if workspace_id is None:
        logger.warning("opportunity_strategy generation skipped workspace_id=None")
        return out

    logger.info("opportunity_strategy generation start workspace_id=%s", workspace_id)
    act_thresh = act_now_threshold if act_now_threshold is not None else DEFAULT_ACT_NOW_SCORE_THRESHOLD
    mon_thresh = monitor_threshold if monitor_threshold is not None else DEFAULT_MONITOR_SCORE_THRESHOLD
    try:
        from amazon_research.workspace_alert_preferences import get_workspace_alert_preferences_with_defaults
        prefs = get_workspace_alert_preferences_with_defaults(workspace_id)
        act_thresh = _safe_float(prefs.get("score_threshold"), DEFAULT_ACT_NOW_SCORE_THRESHOLD)
    except Exception as e:
        logger.debug("opportunity_strategy alert preferences fallback: %s", e)

    try:
        rankings = _get_workspace_rankings(workspace_id)
        portfolio_refs = _get_portfolio_refs(workspace_id)
        alert_refs = _get_alert_refs(workspace_id)
    except Exception as e:
        logger.warning("opportunity_strategy signal gather failed workspace_id=%s: %s", workspace_id, e)
        out["strategy_summary"] = {"total_opportunities": 0, "act_now_count": 0, "monitor_count": 0, "deprioritized_count": 0, "signal_fallback": True}
        out["rationale_summary"] = {"message": "Signals unavailable; run refresh when data is ready."}
        return out

    prioritized: List[Dict[str, Any]] = []
    monitor: List[Dict[str, Any]] = []
    deprioritized: List[Dict[str, Any]] = []

    for r in rankings or []:
        ref = (r.get("opportunity_ref") or "").strip()
        if not ref:
            continue
        score = _safe_float(r.get("opportunity_score"))
        in_portfolio = ref in portfolio_refs or any(ref.endswith(k) or k.endswith(ref) for k in portfolio_refs)
        has_alert = ref in alert_refs
        supporting = {
            "opportunity_score": score,
            "demand_score": r.get("demand_score"),
            "competition_score": r.get("competition_score"),
            "trend_score": r.get("trend_score"),
            "in_portfolio": in_portfolio,
            "has_alert": has_alert,
        }
        status, priority, rationale = _classify_opportunity(ref, score, in_portfolio, has_alert, act_thresh, mon_thresh)
        entry = _build_opportunity_entry(ref, status, priority, rationale, score, in_portfolio, has_alert, supporting)
        if status == STRATEGY_ACT_NOW:
            prioritized.append(entry)
        elif status == STRATEGY_MONITOR:
            monitor.append(entry)
        else:
            deprioritized.append(entry)

    out["prioritized_opportunities"] = prioritized
    out["monitor_opportunities"] = monitor
    out["deprioritized_opportunities"] = deprioritized

    out["strategy_summary"] = {
        "total_opportunities": len(rankings),
        "act_now_count": len(prioritized),
        "monitor_count": len(monitor),
        "deprioritized_count": len(deprioritized),
    }
    out["rationale_summary"] = {
        "act_now_threshold": act_thresh,
        "monitor_threshold": mon_thresh,
        "message": f"Classified by score and portfolio/alert signals; {len(prioritized)} act now, {len(monitor)} monitor, {len(deprioritized)} deprioritized.",
    }
    out["top_actions"] = [
        "Review prioritized opportunities and add high-value items to portfolio.",
        "Monitor mid-score opportunities for trend changes.",
    ][:5]
    out["risk_flags"] = []
    if deprioritized and len(deprioritized) > len(prioritized) + len(monitor):
        out["risk_flags"].append("Many opportunities below monitor threshold; consider broadening criteria.")
    out["confidence_indicators"] = {
        "rankings_used": len(rankings),
        "portfolio_refs_used": len(portfolio_refs),
        "alert_refs_used": len(alert_refs),
    }

    logger.info(
        "opportunity_strategy generation success workspace_id=%s act_now=%s monitor=%s deprioritized=%s",
        workspace_id,
        len(prioritized),
        len(monitor),
        len(deprioritized),
    )
    return out
