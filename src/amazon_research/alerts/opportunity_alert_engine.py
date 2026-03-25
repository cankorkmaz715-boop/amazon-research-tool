"""
Step 107: Opportunity alert engine – detect important opportunity changes from research signals.
Rule-based, explainable. Compatible with market opportunity board, niche explorer, research dashboard.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("alerts.opportunity_alert_engine")

ALERT_NEW_STRONG_CANDIDATE = "new_strong_candidate"
ALERT_OPPORTUNITY_INCREASE = "opportunity_increase"
ALERT_TREND_SCORE_CHANGE = "trend_score_change"
ALERT_COMPETITION_DROP = "competition_drop"
ALERT_DEMAND_INCREASE = "demand_increase"

TARGET_TYPE_CLUSTER = "cluster"
TARGET_TYPE_NICHE = "niche"
TARGET_TYPE_ASIN = "asin"


def _norm_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize board/explorer/MOI entry to common shape: cluster_id, opportunity, demand_score, competition_score, trend_score."""
    cid = entry.get("cluster_id") or entry.get("niche_id") or ""
    opp = entry.get("opportunity_score") or entry.get("opportunity_index") or entry.get("market_opportunity_index") or 0.0
    contrib = entry.get("contributing_signals") or entry.get("core_signals") or {}
    if isinstance(opp, (int, float)):
        opp = float(opp)
    else:
        opp = 0.0
    demand = entry.get("demand_score") if entry.get("demand_score") is not None else contrib.get("demand_score")
    if demand is None:
        demand = 0.0
    try:
        demand = float(demand)
    except (TypeError, ValueError):
        demand = 0.0
    comp = entry.get("competition_score") if entry.get("competition_score") is not None else contrib.get("competition_score")
    if comp is None:
        comp = 0.0
    try:
        comp = float(comp)
    except (TypeError, ValueError):
        comp = 0.0
    trend = entry.get("trend_score") if entry.get("trend_score") is not None else contrib.get("trend_score")
    if trend is None:
        trend = 0.0
    try:
        trend = float(trend)
    except (TypeError, ValueError):
        trend = 0.0
    return {
        "cluster_id": cid,
        "opportunity": opp,
        "demand_score": demand,
        "competition_score": comp,
        "trend_score": trend,
        "label": entry.get("label"),
    }


def _current_by_id(entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index normalized entries by cluster_id."""
    out: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        n = _norm_entry(e)
        cid = n.get("cluster_id") or ""
        if cid and (cid not in out or (n.get("opportunity") or 0) > (out[cid].get("opportunity") or 0)):
            out[cid] = n
    return out


def evaluate_opportunity_alerts(
    current_entries: List[Dict[str, Any]],
    previous_entries: Optional[List[Dict[str, Any]]] = None,
    *,
    thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate alert conditions on current (and optional previous) opportunity/board/explorer entries.
    Returns { alerts: [...], summary: { total, by_type } }. Each alert: alert_id, target_entity, target_type,
    alert_type, triggering_signals, timestamp (ISO). Rule-based and explainable.
    """
    th = thresholds or {}
    min_opportunity = float(th.get("min_opportunity", 60.0))
    min_demand = float(th.get("min_demand", 50.0))
    max_competition = float(th.get("max_competition", 50.0))
    min_trend = float(th.get("min_trend", 40.0))
    opportunity_delta = float(th.get("opportunity_delta", 5.0))
    demand_delta = float(th.get("demand_delta", 5.0))
    competition_drop_delta = float(th.get("competition_drop_delta", 5.0))
    trend_delta = float(th.get("trend_delta", 5.0))

    current = _current_by_id(current_entries)
    previous = _current_by_id(previous_entries or [])
    alerts: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    for cid, cur in current.items():
        if not cid:
            continue
        prev = previous.get(cid)
        label = cur.get("label") or cid

        # New strong candidate: in current, not in previous (or no previous), opportunity above threshold
        if not prev and (cur.get("opportunity") or 0) >= min_opportunity:
            alerts.append({
                "alert_id": str(uuid.uuid4()),
                "target_entity": cid,
                "target_type": TARGET_TYPE_CLUSTER,
                "alert_type": ALERT_NEW_STRONG_CANDIDATE,
                "triggering_signals": {
                    "opportunity": round(cur.get("opportunity") or 0, 1),
                    "min_opportunity": min_opportunity,
                    "reason": f"new candidate {cid!r} opportunity {cur.get('opportunity'):.0f} >= {min_opportunity}",
                },
                "timestamp": now,
            })

        if prev:
            # Opportunity increase
            cur_opp = cur.get("opportunity") or 0
            prev_opp = prev.get("opportunity") or 0
            if cur_opp - prev_opp >= opportunity_delta:
                alerts.append({
                    "alert_id": str(uuid.uuid4()),
                    "target_entity": cid,
                    "target_type": TARGET_TYPE_CLUSTER,
                    "alert_type": ALERT_OPPORTUNITY_INCREASE,
                    "triggering_signals": {
                        "opportunity_current": round(cur_opp, 1),
                        "opportunity_previous": round(prev_opp, 1),
                        "delta": round(cur_opp - prev_opp, 1),
                        "reason": f"opportunity +{cur_opp - prev_opp:.0f}",
                    },
                    "timestamp": now,
                })

            # Demand increase
            cur_d = cur.get("demand_score") or 0
            prev_d = prev.get("demand_score") or 0
            if cur_d - prev_d >= demand_delta:
                alerts.append({
                    "alert_id": str(uuid.uuid4()),
                    "target_entity": cid,
                    "target_type": TARGET_TYPE_CLUSTER,
                    "alert_type": ALERT_DEMAND_INCREASE,
                    "triggering_signals": {
                        "demand_current": round(cur_d, 1),
                        "demand_previous": round(prev_d, 1),
                        "delta": round(cur_d - prev_d, 1),
                        "reason": f"demand +{cur_d - prev_d:.0f}",
                    },
                    "timestamp": now,
                })

            # Competition drop (lower is better)
            cur_c = cur.get("competition_score") or 0
            prev_c = prev.get("competition_score") or 0
            if prev_c - cur_c >= competition_drop_delta:
                alerts.append({
                    "alert_id": str(uuid.uuid4()),
                    "target_entity": cid,
                    "target_type": TARGET_TYPE_CLUSTER,
                    "alert_type": ALERT_COMPETITION_DROP,
                    "triggering_signals": {
                        "competition_current": round(cur_c, 1),
                        "competition_previous": round(prev_c, 1),
                        "delta": round(prev_c - cur_c, 1),
                        "reason": f"competition -{prev_c - cur_c:.0f}",
                    },
                    "timestamp": now,
                })

            # Trend score change (increase)
            cur_t = cur.get("trend_score") or 0
            prev_t = prev.get("trend_score") or 0
            if cur_t - prev_t >= trend_delta:
                alerts.append({
                    "alert_id": str(uuid.uuid4()),
                    "target_entity": cid,
                    "target_type": TARGET_TYPE_CLUSTER,
                    "alert_type": ALERT_TREND_SCORE_CHANGE,
                    "triggering_signals": {
                        "trend_current": round(cur_t, 1),
                        "trend_previous": round(prev_t, 1),
                        "delta": round(cur_t - prev_t, 1),
                        "reason": f"trend +{cur_t - prev_t:.0f}",
                    },
                    "timestamp": now,
                })

    by_type: Dict[str, int] = {}
    for a in alerts:
        t = a.get("alert_type") or ""
        by_type[t] = by_type.get(t, 0) + 1

    try:
        from amazon_research.monitoring import record_alert_generated
        record_alert_generated(len(alerts))
    except Exception:
        pass

    return {
        "alerts": alerts,
        "summary": {"total": len(alerts), "by_type": by_type},
    }
