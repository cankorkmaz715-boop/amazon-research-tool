"""
Step 203: Market entry signals engine – workspace-scoped market entry recommendations.
Deterministic, rule-based; consumes workspace intelligence, strategy, portfolio recommendations.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("market_entry_signals.engine")

STATUS_ENTER_NOW = "enter_now"
STATUS_MONITOR = "monitor_market"
STATUS_DEFER = "defer_market"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# Production markets to evaluate (Step 184)
DEFAULT_MARKETS = ["DE", "US", "AU"]
# Rule thresholds: min opportunity count for enter_now / monitor
ENTER_NOW_MIN_OPPORTUNITIES = 5
MONITOR_MIN_OPPORTUNITIES = 1


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _extract_market(ref: str) -> str:
    """Extract market code from opportunity_ref (e.g. DE:B08 -> DE)."""
    r = (ref or "").strip()
    if ":" in r:
        return r.split(":", 1)[0].strip().upper() or "DE"
    return "DE"


def _count_by_market_from_strategy(strategy: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Return per-market counts: prioritized, monitor, deprioritized."""
    out: Dict[str, Dict[str, int]] = {}
    for lst_key, count_key in (
        ("prioritized_opportunities", "prioritized"),
        ("monitor_opportunities", "monitor"),
        ("deprioritized_opportunities", "deprioritized"),
    ):
        for opp in strategy.get(lst_key) or []:
            ref = (opp.get("opportunity_id") or "").strip()
            if not ref:
                continue
            m = _extract_market(ref)
            if m not in out:
                out[m] = {"prioritized": 0, "monitor": 0, "deprioritized": 0}
            out[m][count_key] = out[m].get(count_key, 0) + 1
    return out


def _count_by_market_from_coverage(market_coverage: Dict[str, Any]) -> Dict[str, int]:
    """Return count_by_market from workspace intelligence market_coverage_overview."""
    count_by = market_coverage.get("count_by_market")
    if isinstance(count_by, dict):
        return dict(count_by)
    return {}


def _build_market_signal_entry(
    market_key: str,
    recommendation_status: str,
    priority_level: str,
    rationale: str,
    supporting_signals: Dict[str, Any],
    recommended_action: str,
    risk_notes: List[str],
) -> Dict[str, Any]:
    return {
        "market_key": market_key,
        "recommendation_status": recommendation_status,
        "priority_level": priority_level,
        "rationale": rationale,
        "supporting_signals": supporting_signals or {},
        "recommended_action": recommended_action,
        "risk_notes": risk_notes or [],
    }


def generate_workspace_market_entry_signals(workspace_id: Optional[int]) -> Dict[str, Any]:
    """
    Produce normalized market-entry signals for a workspace.
    Consumes workspace intelligence (market coverage), opportunity strategy (counts per market), portfolio recommendations.
    Stable shape; empty lists when data missing. Never raises.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "generated_at": _now_utc().isoformat(),
        "market_signals": [],
        "recommended_markets": [],
        "monitor_markets": [],
        "deprioritized_markets": [],
        "market_entry_summary": {},
        "rationale_summary": {},
        "top_market_actions": [],
        "risk_flags": [],
        "confidence_indicators": {},
    }
    if workspace_id is None:
        logger.warning("market_entry_signals generation skipped workspace_id=None")
        return out

    logger.info("market_entry_signals generation start workspace_id=%s", workspace_id)
    strategy: Dict[str, Any] = {}
    market_coverage: Dict[str, Any] = {}
    try:
        from amazon_research.workspace_intelligence import get_workspace_intelligence_summary_prefer_cached
        intel = get_workspace_intelligence_summary_prefer_cached(workspace_id)
        market_coverage = intel.get("market_coverage_overview") or {}
    except Exception as e:
        logger.warning("market_entry_signals intelligence fetch failed workspace_id=%s: %s", workspace_id, e)
    try:
        from amazon_research.opportunity_strategy import generate_workspace_opportunity_strategy
        strategy = generate_workspace_opportunity_strategy(workspace_id)
    except Exception as e:
        logger.warning("market_entry_signals strategy fetch failed workspace_id=%s: %s", workspace_id, e)

    count_by_market = _count_by_market_from_coverage(market_coverage)
    strategy_counts = _count_by_market_from_strategy(strategy)
    all_markets = set(DEFAULT_MARKETS) | set(count_by_market.keys()) | set(strategy_counts.keys())

    recommended: List[Dict[str, Any]] = []
    monitor: List[Dict[str, Any]] = []
    deprioritized: List[Dict[str, Any]] = []
    market_signals: List[Dict[str, Any]] = []

    for market_key in sorted(all_markets):
        total = _safe_int(count_by_market.get(market_key), 0)
        sc = strategy_counts.get(market_key) or {}
        pri = _safe_int(sc.get("prioritized"), 0)
        mon = _safe_int(sc.get("monitor"), 0)
        dep = _safe_int(sc.get("deprioritized"), 0)
        supporting = {
            "opportunity_count": total,
            "prioritized_count": pri,
            "monitor_count": mon,
            "deprioritized_count": dep,
        }
        if total >= ENTER_NOW_MIN_OPPORTUNITIES and (pri + mon) >= 2:
            status = STATUS_ENTER_NOW
            priority = PRIORITY_HIGH
            rationale = f"Strong opportunity count ({total}) and prioritized/monitor signals; consider entering or expanding."
            action = "Evaluate entry or scale existing presence."
            risk_notes: List[str] = []
        elif total >= MONITOR_MIN_OPPORTUNITIES or pri or mon:
            status = STATUS_MONITOR
            priority = PRIORITY_MEDIUM
            rationale = f"Some activity (count={total}); monitor for growth before committing."
            action = "Monitor metrics; defer full entry until signals strengthen."
            risk_notes = []
        else:
            status = STATUS_DEFER
            priority = PRIORITY_LOW
            rationale = "Low or no opportunity signal; defer market entry."
            action = "No action; revisit when data improves."
            risk_notes = []

        entry = _build_market_signal_entry(market_key, status, priority, rationale, supporting, action, risk_notes)
        market_signals.append(entry)
        if status == STATUS_ENTER_NOW:
            recommended.append(entry)
        elif status == STATUS_MONITOR:
            monitor.append(entry)
        else:
            deprioritized.append(entry)

    out["market_signals"] = market_signals
    out["recommended_markets"] = recommended
    out["monitor_markets"] = monitor
    out["deprioritized_markets"] = deprioritized
    out["market_entry_summary"] = {
        "markets_evaluated": len(all_markets),
        "enter_now_count": len(recommended),
        "monitor_count": len(monitor),
        "defer_count": len(deprioritized),
    }
    out["rationale_summary"] = {
        "message": f"Evaluated {len(all_markets)} markets; {len(recommended)} enter now, {len(monitor)} monitor, {len(deprioritized)} defer.",
    }
    out["top_market_actions"] = [
        "Prioritize recommended_markets for entry or expansion.",
        "Monitor monitor_markets for improving signals.",
        "Defer deprioritized_markets until more data is available.",
    ][:5]
    out["risk_flags"] = []
    if not recommended and all_markets:
        out["risk_flags"].append("No market meets enter_now threshold; consider broadening criteria or collecting more data.")
    out["confidence_indicators"] = {
        "intelligence_used": bool(market_coverage),
        "strategy_used": bool(strategy.get("prioritized_opportunities") is not None),
        "markets_evaluated": len(all_markets),
    }

    logger.info(
        "market_entry_signals generation success workspace_id=%s enter_now=%s monitor=%s defer=%s",
        workspace_id,
        len(recommended),
        len(monitor),
        len(deprioritized),
    )
    return out
