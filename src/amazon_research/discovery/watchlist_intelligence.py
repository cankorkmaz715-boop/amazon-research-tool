"""
Step 132: Watchlist intelligence layer – evaluate watched entities over time.
Uses portfolio watch engine, change magnitude, opportunity/lifecycle/trend/competition/demand movement,
confidence score. Produces importance/priority score, change summary, intelligence label.
Lightweight, rule-based, explainable. Dashboard and alert-engine compatible.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.watchlist_intelligence")

LABEL_HIGH_PRIORITY = "high_priority"
LABEL_ATTENTION = "attention"
LABEL_STABLE = "stable"
LABEL_LOW_ACTIVITY = "low_activity"


def _float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _change_magnitude(summary: Dict[str, Any]) -> float:
    """Compute a 0–100 magnitude from supporting_signal_summary (opportunity, demand, competition deltas)."""
    mag = 0.0
    o_prev = _float(summary.get("opportunity_score_previous"))
    o_cur = summary.get("opportunity_score_current")
    if o_prev is not None and o_cur is not None:
        mag += min(100, abs(float(o_cur) - o_prev))
    d_prev = _float(summary.get("demand_previous"))
    d_cur = _float(summary.get("demand_current"))
    if d_prev is not None and d_cur is not None:
        mag += min(50, abs(d_cur - d_prev) * 0.5)
    c_prev = _float(summary.get("competition_previous"))
    c_cur = _float(summary.get("competition_current"))
    if c_prev is not None and c_cur is not None:
        mag += min(50, abs(c_cur - c_prev) * 0.5)
    return min(100.0, mag)


def _build_change_summary(
    change_type: str,
    summary: Dict[str, Any],
) -> str:
    """Build a short detected change summary from change type and supporting_signal_summary."""
    parts: List[str] = []
    if change_type == "no_change":
        return "No significant change detected."
    if change_type == "new_data":
        return "New data available; no previous snapshot to compare."
    if "opportunity_score_previous" in summary and "opportunity_score_current" in summary:
        o_prev = summary["opportunity_score_previous"]
        o_cur = summary["opportunity_score_current"]
        parts.append(f"opportunity score {o_prev} → {o_cur}")
    if "lifecycle_previous" in summary and "lifecycle_current" in summary:
        parts.append(f"lifecycle {summary['lifecycle_previous']} → {summary['lifecycle_current']}")
    if "trend_previous" in summary or "trend_current" in summary:
        parts.append("trend signal updated")
    if "demand_previous" in summary and "demand_current" in summary:
        parts.append(f"demand {summary['demand_previous']} → {summary['demand_current']}")
    if "competition_previous" in summary and "competition_current" in summary:
        parts.append(f"competition {summary['competition_previous']} → {summary['competition_current']}")
    return "; ".join(parts) if parts else f"Change: {change_type}"


def get_watch_intelligence(
    watch_id: int,
    workspace_id: Optional[int] = None,
    *,
    watch_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a watch and produce intelligence output. Uses portfolio watch engine; optionally
    confidence score for cluster/niche. Returns: watch_id, watched_entity, importance_score (0–100),
    detected_change_summary, watch_intelligence_label, timestamp.
    """
    if watch_result is None:
        try:
            from amazon_research.discovery.portfolio_watch_engine import evaluate_watch
            watch_result = evaluate_watch(watch_id, workspace_id=workspace_id)
        except Exception as e:
            logger.debug("get_watch_intelligence evaluate_watch failed: %s", e)
            watch_result = {}
    out: Dict[str, Any] = {
        "watch_id": watch_id,
        "watched_entity": watch_result.get("watched_entity") or {"type": "", "ref": ""},
        "importance_score": 0,
        "detected_change_summary": "",
        "watch_intelligence_label": LABEL_LOW_ACTIVITY,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    change_type = watch_result.get("detected_change_type") or "no_change"
    summary = watch_result.get("supporting_signal_summary") or {}

    # Change magnitude
    magnitude = _change_magnitude(summary)
    if change_type == "new_data":
        magnitude = min(100, magnitude + 30)

    # Confidence score for cluster/niche (boosts reliability of the change)
    confidence_score: Optional[float] = None
    ttype = (out["watched_entity"] or {}).get("type") or ""
    ref = (out["watched_entity"] or {}).get("ref") or ""
    if ttype in ("cluster", "niche") and ref:
        try:
            from amazon_research.discovery.opportunity_confidence import get_opportunity_confidence
            conf = get_opportunity_confidence(ref, workspace_id=workspace_id)
            confidence_score = _float(conf.get("confidence_score"))
        except Exception as e:
            logger.debug("get_watch_intelligence get_opportunity_confidence failed: %s", e)

    # Importance/priority score: base from change type + magnitude, optionally weighted by confidence
    importance = 0.0
    if change_type == "no_change":
        importance = 20.0
    elif change_type == "new_data":
        importance = 40.0 + magnitude * 0.3
    elif change_type == "opportunity_score_change":
        importance = 50.0 + min(40, magnitude * 0.5)
    elif change_type == "lifecycle_change":
        importance = 55.0 + min(35, magnitude * 0.4)
    elif change_type == "trend_change":
        importance = 45.0 + min(35, magnitude * 0.4)
    elif change_type in ("demand_change", "competition_change"):
        importance = 50.0 + min(30, magnitude * 0.4)
    else:
        importance = 30.0 + min(40, magnitude * 0.5)
    if confidence_score is not None:
        importance = importance * (0.7 + 0.3 * (confidence_score / 100.0))
    importance = max(0.0, min(100.0, round(importance, 1)))
    out["importance_score"] = importance

    # Label
    if change_type == "no_change" and (not summary or list(summary.keys()) <= ["current"]):
        out["watch_intelligence_label"] = LABEL_STABLE
    elif importance >= 70:
        out["watch_intelligence_label"] = LABEL_HIGH_PRIORITY
    elif importance >= 40 or change_type not in ("no_change", ""):
        out["watch_intelligence_label"] = LABEL_ATTENTION
    elif importance < 25:
        out["watch_intelligence_label"] = LABEL_LOW_ACTIVITY
    else:
        out["watch_intelligence_label"] = LABEL_STABLE

    out["detected_change_summary"] = _build_change_summary(change_type, summary)
    return out


def list_watch_intelligence(
    workspace_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    List all watches for the workspace with intelligence. Returns list of intelligence outputs
    (watch_id, watched_entity, importance_score, detected_change_summary, watch_intelligence_label, timestamp).
    Sorted by importance_score descending for dashboard.
    """
    try:
        from amazon_research.db import list_watches
        from amazon_research.discovery.portfolio_watch_engine import evaluate_watch
    except Exception as e:
        logger.debug("list_watch_intelligence import failed: %s", e)
        return []
    watches = list_watches(workspace_id, limit=limit)
    results: List[Dict[str, Any]] = []
    for w in watches:
        wid = w.get("id")
        if wid is None:
            continue
        watch_result = evaluate_watch(wid, workspace_id=workspace_id)
        results.append(get_watch_intelligence(wid, workspace_id=workspace_id, watch_result=watch_result))
    results.sort(key=lambda x: (-(x.get("importance_score") or 0), x.get("watch_id") or 0))
    return results
