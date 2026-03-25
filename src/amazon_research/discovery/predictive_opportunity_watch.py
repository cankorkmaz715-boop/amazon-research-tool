"""
Step 174: Predictive opportunity watch – identify early-stage candidates that may become strong opportunities.
Early signals: increasing trend, improving demand, stable/slow competition, emerging niches, emerging/rising lifecycle.
Uses lifecycle engine, signal drift detector, trend/score history, niche clustering. Classifies: early_watch, watchlist, rising_candidate.
Integrates with workspace opportunity feed, opportunity memory, anomaly alert engine, copilot suggestion system.
Rule-based, lightweight. Does not modify crawler, worker, auth, billing, UI.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.predictive_opportunity_watch")

# Watch classifications
CLASS_EARLY_WATCH = "early_watch"
CLASS_WATCHLIST = "watchlist"
CLASS_RISING_CANDIDATE = "rising_candidate"

WATCH_CLASSIFICATIONS = [CLASS_EARLY_WATCH, CLASS_WATCHLIST, CLASS_RISING_CANDIDATE]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_trend(score_history: Sequence[Any], last_n: int = 5) -> str:
    """Return 'up', 'down', or 'flat' from recent score history."""
    if not score_history or not isinstance(score_history, (list, tuple)):
        return "flat"
    points: List[float] = []
    for p in score_history:
        if isinstance(p, (int, float)):
            points.append(float(p))
        elif isinstance(p, dict) and p.get("score") is not None:
            try:
                points.append(float(p["score"]))
            except (TypeError, ValueError):
                pass
    points = points[-last_n:] if len(points) > last_n else points
    if len(points) < 2:
        return "flat"
    first, last = points[0], points[-1]
    if last > first:
        return "up"
    if last < first:
        return "down"
    return "flat"


def get_predictive_watch(
    opportunity_ref: str,
    *,
    memory_record: Optional[Dict[str, Any]] = None,
    lifecycle_output: Optional[Dict[str, Any]] = None,
    drift_reports: Optional[Sequence[Dict[str, Any]]] = None,
    trend_direction: Optional[str] = None,
    demand_trend: Optional[str] = None,
    competition_trend: Optional[str] = None,
    niche_emerging: bool = False,
) -> Dict[str, Any]:
    """
    Classify opportunity as early_watch, watchlist, or rising_candidate. Returns:
    opportunity_id, watch_classification, predictive_confidence, signal_summary, timestamp.
    """
    ref = (opportunity_ref or "").strip()
    out: Dict[str, Any] = {
        "opportunity_id": ref,
        "watch_classification": CLASS_WATCHLIST,
        "predictive_confidence": 50,
        "signal_summary": {},
        "timestamp": _now_iso(),
    }
    if not ref:
        out["signal_summary"] = {"error": "missing ref"}
        return out

    mem = memory_record
    if mem is None:
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
        except Exception as e:
            logger.debug("get_predictive_watch get_opportunity_memory: %s", e)

    life = lifecycle_output
    if life is None and mem:
        try:
            from amazon_research.discovery.opportunity_lifecycle_engine import get_lifecycle_state
            life = get_lifecycle_state(ref, memory_record=mem)
        except Exception as e:
            logger.debug("get_predictive_watch get_lifecycle_state: %s", e)

    score_history = (mem or {}).get("score_history") or []
    score_trend = _score_trend(score_history)
    trend_dir = (trend_direction or "").strip().lower() or score_trend
    demand_dir = (demand_trend or "").strip().lower() or "flat"
    comp_dir = (competition_trend or "").strip().lower() or "flat"

    lifecycle_state = (life or {}).get("lifecycle_state") or ""
    lifecycle_score = (life or {}).get("lifecycle_score") or 50
    supporting = (life or {}).get("supporting_signal_summary") or {}

    # Build signal summary
    signal_summary: Dict[str, Any] = {
        "lifecycle_state": lifecycle_state,
        "lifecycle_score": lifecycle_score,
        "score_trend": score_trend,
        "trend_direction": trend_dir,
        "demand_trend": demand_dir,
        "competition_trend": comp_dir,
        "niche_emerging": niche_emerging,
        "score_history_length": len(score_history) if isinstance(score_history, list) else 0,
    }
    if drift_reports:
        signal_summary["drift_count"] = len(drift_reports)
        signal_summary["drift_has_spike"] = any((d.get("drift_type") or "").lower() == "spike" for d in drift_reports)
        signal_summary["drift_has_collapse"] = any((d.get("drift_type") or "").lower() == "collapse" for d in drift_reports)
    out["signal_summary"] = signal_summary

    # Rule-based classification
    # Exclude weakening/fading from predictive watch
    if lifecycle_state in ("weakening", "fading"):
        out["watch_classification"] = CLASS_WATCHLIST
        out["predictive_confidence"] = max(10, min(30, lifecycle_score))
        return out

    # Rising candidate: lifecycle rising/accelerating + trend up + (demand up or stable competition)
    if lifecycle_state in ("rising", "accelerating") and trend_dir == "up":
        conf = min(90, 50 + (lifecycle_score or 0) // 2)
        if demand_dir == "up":
            conf = min(95, conf + 10)
        if comp_dir in ("flat", "down"):
            conf = min(95, conf + 5)
        out["watch_classification"] = CLASS_RISING_CANDIDATE
        out["predictive_confidence"] = conf
        return out

    # Early watch: emerging lifecycle or niche_emerging + (trend flat/up, no collapse)
    if lifecycle_state == "emerging" or niche_emerging:
        if (drift_reports and signal_summary.get("drift_has_collapse")) or trend_dir == "down":
            out["watch_classification"] = CLASS_WATCHLIST
            out["predictive_confidence"] = max(25, min(45, lifecycle_score))
        else:
            out["watch_classification"] = CLASS_EARLY_WATCH
            out["predictive_confidence"] = max(35, min(65, 40 + (lifecycle_score or 0) // 3))
        return out

    # Watchlist: maturing/stable with up trend or improving demand
    if lifecycle_state in ("maturing", "stable") and (trend_dir == "up" or demand_dir == "up"):
        out["watch_classification"] = CLASS_WATCHLIST
        out["predictive_confidence"] = max(45, min(70, lifecycle_score or 50))
        return out

    # Default: watchlist with moderate confidence
    out["watch_classification"] = CLASS_WATCHLIST
    out["predictive_confidence"] = max(30, min(60, lifecycle_score or 50))
    return out


def list_predictive_watch_candidates(
    workspace_id: Optional[int] = None,
    limit: int = 50,
    watch_classification: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List opportunities with predictive watch classification. Uses opportunity memory and lifecycle engine.
    Optional filter by watch_classification (early_watch, watchlist, rising_candidate).
    """
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
        out: List[Dict[str, Any]] = []
        for mem in rows:
            ref = mem.get("opportunity_ref")
            if not ref:
                continue
            watch = get_predictive_watch(ref, memory_record=mem)
            if watch_classification is not None and watch.get("watch_classification") != watch_classification:
                continue
            out.append({**mem, "predictive_watch": watch})
        return out
    except Exception as e:
        logger.debug("list_predictive_watch_candidates: %s", e)
        return []


def to_feed_item(watch_output: Dict[str, Any], workspace_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Convert predictive watch output to a form suitable for workspace opportunity feed
    (opportunity_id, watch_classification, predictive_confidence, signal_summary, timestamp).
    """
    return {
        "workspace_id": workspace_id,
        "feed_item_type": "predictive_watch",
        "target_entity": {"ref": watch_output.get("opportunity_id"), "type": "opportunity"},
        "priority_score": watch_output.get("predictive_confidence") or 50,
        "short_explanation": f"Predictive watch: {watch_output.get('watch_classification', 'watchlist')} (confidence {watch_output.get('predictive_confidence', 50)})",
        "timestamp": watch_output.get("timestamp"),
        "opportunity_id": watch_output.get("opportunity_id"),
        "watch_classification": watch_output.get("watch_classification"),
        "predictive_confidence": watch_output.get("predictive_confidence"),
        "signal_summary": watch_output.get("signal_summary"),
    }
