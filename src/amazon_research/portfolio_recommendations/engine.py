"""
Step 202: Portfolio recommendation engine – workspace-scoped add/monitor/archive recommendations.
Rule-based, deterministic; consumes portfolio tracking, opportunity strategy, rankings, alerts.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from amazon_research.logging_config import get_logger

logger = get_logger("portfolio_recommendations.engine")

RECOMMEND_ADD = "add_to_portfolio"
RECOMMEND_MONITOR = "continue_monitoring"
RECOMMEND_ARCHIVE = "archive_or_deprioritize"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_ref(key: str) -> str:
    """Normalize item_key or opportunity_id for matching."""
    k = (key or "").strip()
    if not k:
        return ""
    if ":" in k:
        return k
    return f"DE:{k}"


def _portfolio_key_set(items: List[Dict[str, Any]]) -> Set[str]:
    """Set of normalized keys (item_key and DE:item_key) for portfolio items."""
    out: Set[str] = set()
    for it in items or []:
        key = (it.get("item_key") or "").strip()
        if key:
            out.add(key)
            out.add(_normalize_ref(key))
    return out


def _build_recommendation_entry(
    item_type: str,
    item_key: str,
    item_label: Optional[str],
    recommendation_status: str,
    priority_level: str,
    rationale: str,
    supporting_signals: Dict[str, Any],
    recommended_action: str,
    risk_notes: List[str],
) -> Dict[str, Any]:
    return {
        "item_type": item_type or "opportunity",
        "item_key": item_key,
        "item_label": item_label,
        "recommendation_status": recommendation_status,
        "priority_level": priority_level,
        "rationale": rationale,
        "supporting_signals": supporting_signals or {},
        "recommended_action": recommended_action,
        "risk_notes": risk_notes or [],
    }


def generate_workspace_portfolio_recommendations(workspace_id: Optional[int]) -> Dict[str, Any]:
    """
    Produce normalized portfolio recommendation output for a workspace.
    Consumes strategy (prioritized/monitor/deprioritized) and current portfolio; outputs add/monitor/archive lists.
    Stable shape; empty lists when data missing. Never raises.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "generated_at": _now_utc().isoformat(),
        "add_recommendations": [],
        "monitor_recommendations": [],
        "archive_recommendations": [],
        "recommendation_summary": {},
        "rationale_summary": {},
        "top_portfolio_actions": [],
        "risk_flags": [],
        "confidence_indicators": {},
    }
    if workspace_id is None:
        logger.warning("portfolio_recommendations generation skipped workspace_id=None")
        return out

    logger.info("portfolio_recommendations generation start workspace_id=%s", workspace_id)
    try:
        from amazon_research.opportunity_strategy import generate_workspace_opportunity_strategy
        strategy = generate_workspace_opportunity_strategy(workspace_id)
    except Exception as e:
        logger.warning("portfolio_recommendations strategy fetch failed workspace_id=%s: %s", workspace_id, e)
        out["recommendation_summary"] = {"add_count": 0, "monitor_count": 0, "archive_count": 0, "signal_fallback": True}
        out["rationale_summary"] = {"message": "Strategy unavailable; run strategy refresh first."}
        return out

    try:
        from amazon_research.db.workspace_portfolio import list_workspace_portfolio_items
        portfolio_items = list_workspace_portfolio_items(workspace_id, status="active", limit=1000)
    except Exception as e:
        logger.warning("portfolio_recommendations portfolio fetch failed workspace_id=%s: %s", workspace_id, e)
        portfolio_items = []

    in_portfolio = _portfolio_key_set(portfolio_items)
    prioritized = strategy.get("prioritized_opportunities") or []
    monitor_opps = strategy.get("monitor_opportunities") or []
    deprioritized = strategy.get("deprioritized_opportunities") or []

    add_recs: List[Dict[str, Any]] = []
    monitor_recs: List[Dict[str, Any]] = []
    archive_recs: List[Dict[str, Any]] = []

    # Add: high-priority opportunities not yet in portfolio
    for opp in prioritized + monitor_opps:
        ref = (opp.get("opportunity_id") or "").strip()
        if not ref:
            continue
        if ref in in_portfolio or _normalize_ref(ref) in in_portfolio:
            continue
        sig = opp.get("supporting_signals") or {}
        add_recs.append(_build_recommendation_entry(
            item_type="opportunity",
            item_key=ref,
            item_label=None,
            recommendation_status=RECOMMEND_ADD,
            priority_level=opp.get("priority_level") or PRIORITY_HIGH,
            rationale=opp.get("rationale") or "High or medium priority; not yet in portfolio.",
            supporting_signals=sig,
            recommended_action="Add to portfolio and track.",
            risk_notes=opp.get("risk_notes") or [],
        ))

    # Monitor: portfolio items that appear in prioritized or monitor strategy lists
    strategy_refs_keep = {_normalize_ref(o.get("opportunity_id") or "") for o in prioritized + monitor_opps}
    for it in portfolio_items:
        key = (it.get("item_key") or "").strip()
        if not key:
            continue
        nkey = _normalize_ref(key)
        if nkey in strategy_refs_keep or key in strategy_refs_keep:
            opp_entry = next((o for o in prioritized + monitor_opps if _normalize_ref(o.get("opportunity_id") or "") == nkey or (o.get("opportunity_id") or "").strip() == key), None)
            rationale = (opp_entry.get("rationale") or "Keep in portfolio; continue monitoring.") if opp_entry else "In portfolio; continue monitoring."
            priority = (opp_entry.get("priority_level") or PRIORITY_MEDIUM) if opp_entry else PRIORITY_MEDIUM
            sig = (opp_entry.get("supporting_signals") or {}) if opp_entry else {}
            monitor_recs.append(_build_recommendation_entry(
                item_type=it.get("item_type") or "opportunity",
                item_key=key,
                item_label=it.get("item_label"),
                recommendation_status=RECOMMEND_MONITOR,
                priority_level=priority,
                rationale=rationale,
                supporting_signals=sig,
                recommended_action="Monitor metrics; no change needed.",
                risk_notes=(opp_entry.get("risk_notes") or []) if opp_entry else [],
            ))

    # Archive: portfolio items in deprioritized or not in strategy (low value)
    deprioritized_refs = {_normalize_ref(o.get("opportunity_id") or "") for o in deprioritized}
    for it in portfolio_items:
        key = (it.get("item_key") or "").strip()
        if not key:
            continue
        nkey = _normalize_ref(key)
        if nkey in strategy_refs_keep or key in strategy_refs_keep:
            continue
        in_deprioritized = nkey in deprioritized_refs or key in deprioritized_refs
        opp_entry = next((o for o in deprioritized if _normalize_ref(o.get("opportunity_id") or "") == nkey or (o.get("opportunity_id") or "").strip() == key), None)
        rationale = (opp_entry.get("rationale") or "Below monitor threshold; consider archiving.") if opp_entry else "Not in high-priority strategy; consider archiving if no longer relevant."
        sig = (opp_entry.get("supporting_signals") or {}) if opp_entry else {}
        archive_recs.append(_build_recommendation_entry(
            item_type=it.get("item_type") or "opportunity",
            item_key=key,
            item_label=it.get("item_label"),
            recommendation_status=RECOMMEND_ARCHIVE,
            priority_level=PRIORITY_LOW,
            rationale=rationale,
            supporting_signals=sig,
            recommended_action="Review and archive if no longer needed.",
            risk_notes=(opp_entry.get("risk_notes") or []) if opp_entry else [],
        ))

    out["add_recommendations"] = add_recs
    out["monitor_recommendations"] = monitor_recs
    out["archive_recommendations"] = archive_recs
    out["recommendation_summary"] = {
        "add_count": len(add_recs),
        "monitor_count": len(monitor_recs),
        "archive_count": len(archive_recs),
        "portfolio_active_count": len(portfolio_items),
    }
    out["rationale_summary"] = {
        "message": f"Add {len(add_recs)} candidates; continue monitoring {len(monitor_recs)}; consider archiving {len(archive_recs)}.",
    }
    out["top_portfolio_actions"] = [
        "Add high-priority opportunities from add_recommendations to your portfolio.",
        "Keep monitoring items in monitor_recommendations.",
        "Review archive_recommendations and archive items no longer needed.",
    ][:5]
    out["risk_flags"] = []
    if archive_recs and len(archive_recs) > len(monitor_recs):
        out["risk_flags"].append("Many items suggested for archive; review before archiving.")
    out["confidence_indicators"] = {
        "strategy_used": True,
        "portfolio_items_used": len(portfolio_items),
    }

    logger.info(
        "portfolio_recommendations generation success workspace_id=%s add=%s monitor=%s archive=%s",
        workspace_id,
        len(add_recs),
        len(monitor_recs),
        len(archive_recs),
    )
    return out
