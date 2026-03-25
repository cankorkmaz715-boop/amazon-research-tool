"""
Step 172: Opportunity lifecycle engine – richer lifecycle classification using historical and current signals.
States: emerging, rising, accelerating, maturing, saturated, weakening, fading.
Uses opportunity memory, score history, confidence, trend/drift, demand vs competition.
Integrates with opportunity memory, ranking stabilizer, signal drift detector, workspace opportunity feed, alert engine.
Lightweight, deterministic, rule-based. Extensible for predictive lifecycle modeling.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_lifecycle_engine")

# Lifecycle states (richer set)
STATE_EMERGING = "emerging"
STATE_RISING = "rising"
STATE_ACCELERATING = "accelerating"
STATE_MATURING = "maturing"
STATE_SATURATED = "saturated"
STATE_WEAKENING = "weakening"
STATE_FADING = "fading"

LIFECYCLE_STATES = [
    STATE_EMERGING,
    STATE_RISING,
    STATE_ACCELERATING,
    STATE_MATURING,
    STATE_SATURATED,
    STATE_WEAKENING,
    STATE_FADING,
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_trend(score_history: List[Any], last_n: int = 5) -> str:
    """Return 'up', 'down', or 'flat' from recent score history."""
    if not score_history or not isinstance(score_history, list):
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
    try:
        first, last = float(first), float(last)
    except (TypeError, ValueError):
        return "flat"
    if last > first:
        return "up"
    if last < first:
        return "down"
    return "flat"


def _get_drift_for_opportunity(memory_record: Optional[Dict[str, Any]], opportunity_ref: str) -> List[Dict[str, Any]]:
    """Build current + history from memory and run drift checks. Returns list of drift reports."""
    if not memory_record:
        return []
    try:
        from amazon_research.monitoring.signal_drift_detector import run_drift_checks
        score_history = memory_record.get("score_history") or []
        if not isinstance(score_history, list) or len(score_history) < 2:
            return []
        # Build context-style history from score_history
        hist = [{"opportunity_index": p.get("score") if isinstance(p, dict) else p} for p in score_history[:-1]]
        cur = score_history[-1]
        current_ctx = {"opportunity_index": cur.get("score") if isinstance(cur, dict) else cur}
        out = run_drift_checks(current_context=current_ctx, history_contexts=hist, target_id=opportunity_ref)
        return out.get("drifts") or []
    except Exception as e:
        logger.debug("_get_drift_for_opportunity: %s", e)
        return []


def get_lifecycle_state(
    opportunity_ref: str,
    *,
    memory_record: Optional[Dict[str, Any]] = None,
    base_lifecycle: Optional[Dict[str, Any]] = None,
    confidence_record: Optional[Dict[str, Any]] = None,
    drift_reports: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Classify opportunity into richer lifecycle state. Returns:
    opportunity_id, lifecycle_state, lifecycle_score, supporting_signal_summary, timestamp.
    """
    ref = (opportunity_ref or "").strip()
    out: Dict[str, Any] = {
        "opportunity_id": ref,
        "lifecycle_state": STATE_MATURING,
        "lifecycle_score": 50,
        "supporting_signal_summary": {},
        "timestamp": _now_iso(),
    }
    if not ref:
        out["supporting_signal_summary"] = {"error": "missing ref"}
        return out

    mem = memory_record
    if mem is None:
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
        except Exception as e:
            logger.debug("get_lifecycle_state get_opportunity_memory: %s", e)

    base = base_lifecycle
    if base is None and mem:
        try:
            from amazon_research.discovery.opportunity_lifecycle import get_opportunity_lifecycle
            base = get_opportunity_lifecycle(ref, memory_record=mem)
        except Exception as e:
            logger.debug("get_lifecycle_state get_opportunity_lifecycle: %s", e)

    conf = confidence_record
    if conf is None and mem:
        try:
            from amazon_research.discovery.opportunity_confidence import get_opportunity_confidence
            conf = get_opportunity_confidence(ref, memory_record=mem)
        except Exception as e:
            logger.debug("get_lifecycle_state get_opportunity_confidence: %s", e)

    drifts = drift_reports if drift_reports is not None else _get_drift_for_opportunity(mem, ref)
    score_history = (mem or {}).get("score_history") or []
    score_trend = _score_trend(score_history)
    base_state = (base or {}).get("lifecycle_state") or ""
    confidence_label = (conf or {}).get("confidence_label") or "medium"
    confidence_score = (conf or {}).get("confidence_score") or 50
    latest_score = (mem or {}).get("latest_opportunity_score")
    if latest_score is not None:
        try:
            latest_score = float(latest_score)
        except (TypeError, ValueError):
            latest_score = None

    # Build supporting signal summary
    supporting: Dict[str, Any] = {
        "base_lifecycle_state": base_state,
        "score_trend": score_trend,
        "confidence_label": confidence_label,
        "confidence_score": confidence_score,
        "score_history_length": len(score_history) if isinstance(score_history, list) else 0,
        "latest_opportunity_score": latest_score,
    }
    if drifts:
        supporting["drift_types"] = list({d.get("drift_type") for d in drifts if d.get("drift_type")})
        supporting["drift_count"] = len(drifts)
    out["supporting_signal_summary"] = supporting

    # Map to richer state (rule-based)
    # Fading: base is fading or last_seen very old
    if base_state == "fading" or (base or {}).get("rationale", "").lower().find("last_seen") >= 0 and (supporting.get("score_history_length") or 0) == 0:
        out["lifecycle_state"] = STATE_FADING
        out["lifecycle_score"] = min(30, confidence_score)
        return out

    # Weakening: base weakening or score trend down or collapse drift
    if base_state == "weakening" or score_trend == "down":
        out["lifecycle_state"] = STATE_WEAKENING
        out["lifecycle_score"] = max(20, min(45, confidence_score))
        if any(d.get("drift_type") == "collapse" for d in drifts):
            out["lifecycle_score"] = max(10, out["lifecycle_score"] - 15)
        return out

    # Emerging: base new, few observations, not yet rising strongly
    if base_state == "new" and (supporting.get("score_history_length") or 0) <= 2:
        out["lifecycle_state"] = STATE_EMERGING
        out["lifecycle_score"] = min(55, 30 + (confidence_score or 0) // 2)
        return out

    # Accelerating: rising + spike/sudden_shift drift
    if (base_state == "rising" or score_trend == "up") and any(
        d.get("drift_type") in ("spike", "sudden_shift") for d in drifts
    ):
        out["lifecycle_state"] = STATE_ACCELERATING
        out["lifecycle_score"] = min(95, (confidence_score or 50) + 25)
        return out

    # Rising: base rising or score trend up
    if base_state == "rising" or score_trend == "up":
        out["lifecycle_state"] = STATE_RISING
        out["lifecycle_score"] = min(85, (confidence_score or 50) + 15)
        return out

    # Saturated: stable + high score + flat trend
    if base_state == "stable" and score_trend == "flat" and (latest_score or 0) >= 65:
        out["lifecycle_state"] = STATE_SATURATED
        out["lifecycle_score"] = max(50, min(75, (confidence_score or 50)))
        return out

    # Maturing: stable, good score
    if base_state == "stable" or base_state == "new":
        out["lifecycle_state"] = STATE_MATURING
        out["lifecycle_score"] = max(45, min(70, (confidence_score or 50)))
        return out

    out["lifecycle_state"] = STATE_MATURING
    out["lifecycle_score"] = max(40, min(60, confidence_score or 50))
    return out


def list_opportunities_with_lifecycle_engine(
    limit: int = 50,
    lifecycle_state: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    List opportunities with richer lifecycle classification. Compatible with workspace opportunity feed.
    Returns list of { opportunity_ref, lifecycle_state, lifecycle_score, supporting_signal_summary, timestamp, ... memory fields }.
    """
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
        out: List[Dict[str, Any]] = []
        for mem in rows:
            ref = mem.get("opportunity_ref")
            if not ref:
                continue
            life = get_lifecycle_state(ref, memory_record=mem)
            if lifecycle_state is not None and life.get("lifecycle_state") != lifecycle_state:
                continue
            out.append({**mem, "lifecycle_engine": life, "lifecycle_state": life.get("lifecycle_state")})
        return out
    except Exception as e:
        logger.debug("list_opportunities_with_lifecycle_engine: %s", e)
        return []


def get_lifecycle_for_feed(opportunity_ref: str, memory_record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Return lifecycle engine output in a form suitable for workspace opportunity feed (opportunity_id, lifecycle_state, lifecycle_score, supporting_signal_summary, timestamp).
    """
    return get_lifecycle_state(opportunity_ref, memory_record=memory_record)
