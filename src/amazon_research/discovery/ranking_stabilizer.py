"""
Step 129: Opportunity ranking stabilizer – reduce unnecessary volatility in opportunity rankings.
Uses confidence, lifecycle stability, historical score evolution, repeated detections.
Rule-based, explainable. Compatible with opportunity board, niche explorer, dashboard, alert engine.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.ranking_stabilizer")

# Number of recent score_history points to use for stabilization
STABILIZE_HISTORY_LEN = 5
# Default pull toward center when confidence is low (no history)
LOW_CONFIDENCE_CENTER = 50.0


def _float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _recent_scores(score_history: List[Dict[str, Any]], last_n: int = STABILIZE_HISTORY_LEN) -> List[float]:
    """Extract numeric scores from score_history, most recent last_n."""
    if not score_history or not isinstance(score_history, list):
        return []
    scores = []
    for entry in score_history:
        s = entry.get("score") if isinstance(entry, dict) else None
        if s is not None:
            f = _float(s)
            if f is not None:
                scores.append(f)
    return scores[-last_n:] if len(scores) > last_n else scores


def get_stabilized_ranking(
    opportunity_ref: str,
    *,
    raw_score: Optional[float] = None,
    workspace_id: Optional[int] = None,
    memory_record: Optional[Dict[str, Any]] = None,
    confidence_record: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Produce a stabilized ranking entry for one opportunity. Reduces volatility using
    confidence, lifecycle, and historical score evolution.
    Returns: opportunity_id, raw_score, stabilized_score, explanation (stabilization factors).
    """
    ref = (opportunity_ref or "").strip()
    out: Dict[str, Any] = {
        "opportunity_id": ref,
        "raw_score": None,
        "stabilized_score": None,
        "explanation": "",
    }
    if not ref:
        out["explanation"] = "Missing opportunity reference."
        return out

    mem = memory_record
    if mem is None:
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
        except Exception as e:
            logger.debug("get_stabilized_ranking get_opportunity_memory failed: %s", e)
    if workspace_id is not None and mem and mem.get("workspace_id") is not None and mem.get("workspace_id") != workspace_id:
        mem = None

    raw = raw_score
    if raw is None and mem:
        raw = _float(mem.get("latest_opportunity_score"))
    if raw is None:
        raw = 0.0
    raw = max(0.0, min(100.0, float(raw)))
    out["raw_score"] = round(raw, 1)

    score_history = (mem or {}).get("score_history") or []
    recent = _recent_scores(score_history, STABILIZE_HISTORY_LEN)
    n_observations = len(recent)

    conf = confidence_record
    if conf is None:
        try:
            from amazon_research.discovery.opportunity_confidence import get_opportunity_confidence
            conf = get_opportunity_confidence(ref, workspace_id=workspace_id, memory_record=mem)
        except Exception as e:
            logger.debug("get_stabilized_ranking get_opportunity_confidence failed: %s", e)
    confidence_label = (conf or {}).get("confidence_label") or "low"
    confidence_score = _float((conf or {}).get("confidence_score")) or 0

    lifecycle_state = ""
    try:
        from amazon_research.discovery.opportunity_lifecycle import get_opportunity_lifecycle
        life = get_opportunity_lifecycle(ref, memory_record=mem)
        lifecycle_state = (life.get("lifecycle_state") or "").strip()
    except Exception as e:
        logger.debug("get_stabilized_ranking get_opportunity_lifecycle failed: %s", e)

    # Stabilization: blend raw with historical central tendency to reduce spikes
    stabilized = raw
    factors: List[str] = []

    if n_observations >= 3:
        # Use median of recent + raw to dampen short-term spikes
        combined = recent + [raw]
        combined.sort()
        mid = len(combined) // 2
        if len(combined) % 2:
            median_val = combined[mid]
        else:
            median_val = (combined[mid - 1] + combined[mid]) / 2.0
        # Weight: high confidence -> trust raw more; low -> trust median more
        if confidence_label == "high":
            blend = 0.7 * raw + 0.3 * median_val
        elif confidence_label == "medium":
            blend = 0.5 * raw + 0.5 * median_val
        else:
            blend = 0.3 * raw + 0.7 * median_val
        stabilized = blend
        factors.append(f"median_blend(n={n_observations})")
    elif n_observations >= 1:
        hist_avg = sum(recent) / len(recent)
        # Light blend with history
        if confidence_label == "high":
            stabilized = 0.8 * raw + 0.2 * hist_avg
        else:
            stabilized = 0.6 * raw + 0.4 * hist_avg
        factors.append(f"avg_blend(n={n_observations})")
    else:
        # No history: low confidence -> pull toward center to avoid over-ranking single observations
        if confidence_label == "low" and confidence_score < 40:
            stabilized = 0.7 * raw + 0.3 * LOW_CONFIDENCE_CENTER
            factors.append("low_confidence_pull_to_center")
        else:
            factors.append("no_history")

    stabilized = max(0.0, min(100.0, stabilized))
    out["stabilized_score"] = round(stabilized, 1)

    factors.append(f"confidence={confidence_label}")
    if lifecycle_state:
        factors.append(f"lifecycle={lifecycle_state}")
    out["explanation"] = "; ".join(factors)

    return out


def get_stabilized_rankings(
    opportunity_refs: Optional[List[str]] = None,
    *,
    workspace_id: Optional[int] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Produce stabilized ranking entries for a list of opportunities (or all from memory if refs not given).
    Returns list of { opportunity_id, raw_score, stabilized_score, explanation } sorted by stabilized_score descending.
    Board-compatible: can be used to re-rank opportunity board by stabilized score.
    """
    refs = opportunity_refs
    if refs is None:
        try:
            from amazon_research.db import list_opportunity_memory
            rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
            refs = [r.get("opportunity_ref") for r in rows if r.get("opportunity_ref")]
        except Exception as e:
            logger.debug("get_stabilized_rankings list_opportunity_memory failed: %s", e)
            return []
    if not refs:
        return []
    out: List[Dict[str, Any]] = []
    for ref in refs:
        if not ref:
            continue
        out.append(get_stabilized_ranking(ref, workspace_id=workspace_id))
    out.sort(key=lambda x: (-(x.get("stabilized_score") or 0), x.get("opportunity_id") or ""))
    return out
