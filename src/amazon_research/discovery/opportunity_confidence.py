"""
Step 128: Opportunity confidence scoring – estimate reliability of each opportunity candidate.
Uses supporting data volume, repeated detections, lifecycle stability, trend history length,
cluster density, signal consistency. Rule-based, explainable.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_confidence")

CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"

# Score thresholds for label
SCORE_LOW_MAX = 39
SCORE_MEDIUM_MAX = 69


def get_opportunity_confidence(
    opportunity_ref: str,
    *,
    workspace_id: Optional[int] = None,
    memory_record: Optional[Dict[str, Any]] = None,
    explanation_record: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Estimate reliability of an opportunity candidate from available signals.
    Returns: opportunity_id, confidence_score (0–100), confidence_label (low|medium|high),
    explanation (compact string), contributing_signals (dict).
    """
    ref = (opportunity_ref or "").strip()
    out: Dict[str, Any] = {
        "opportunity_id": ref,
        "confidence_score": 0,
        "confidence_label": CONFIDENCE_LOW,
        "explanation": "",
        "contributing_signals": {},
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
            logger.debug("get_opportunity_confidence get_opportunity_memory failed: %s", e)
    if workspace_id is not None and mem and mem.get("workspace_id") is not None and mem.get("workspace_id") != workspace_id:
        mem = None

    # Amount of supporting data: score_history length + memory presence
    score_history = (mem or {}).get("score_history") or []
    supporting_data_count = len(score_history) if isinstance(score_history, list) else 0
    if mem:
        supporting_data_count += 1
    contributing: Dict[str, Any] = {"supporting_data_count": supporting_data_count}

    # Repeated discovery detections (same as score_history length for "times seen")
    repeated_detections = len(score_history) if isinstance(score_history, list) else 0
    contributing["repeated_detections"] = repeated_detections

    # Lifecycle stability
    lifecycle_state = ""
    try:
        from amazon_research.discovery.opportunity_lifecycle import get_opportunity_lifecycle
        life = get_opportunity_lifecycle(ref, memory_record=mem)
        lifecycle_state = (life.get("lifecycle_state") or "").strip()
    except Exception as e:
        logger.debug("get_opportunity_confidence get_opportunity_lifecycle failed: %s", e)
    contributing["lifecycle_stability"] = lifecycle_state
    # stable/rising/new -> positive; weakening/fading -> negative

    # Trend history length
    trend_history_length = 0
    try:
        from amazon_research.db import get_trend_result_history
        trend_history = get_trend_result_history("cluster", ref, limit=50)
        trend_history_length = len(trend_history) if isinstance(trend_history, list) else 0
    except Exception as e:
        logger.debug("get_opportunity_confidence get_trend_result_history failed: %s", e)
    contributing["trend_history_length"] = trend_history_length

    # Cluster density (member count for this cluster from cache)
    cluster_density = 0
    try:
        from amazon_research.db import get_cluster_cache
        entry = get_cluster_cache("default")
        if entry:
            clusters = entry.get("clusters") or []
            for c in clusters:
                if str(c.get("cluster_id") or "") == ref or str(c.get("cluster_id") or "") == str(ref):
                    cluster_density = len(c.get("member_asins") or [])
                    break
    except Exception as e:
        logger.debug("get_opportunity_confidence get_cluster_cache failed: %s", e)
    contributing["cluster_density"] = cluster_density

    # Signal consistency from explainability (positive vs negative contributions)
    if explanation_record is None:
        try:
            from amazon_research.discovery.opportunity_explainability import get_opportunity_explanation
            explanation_record = get_opportunity_explanation(ref, workspace_id=workspace_id, memory_record=mem)
        except Exception as e:
            logger.debug("get_opportunity_confidence get_opportunity_explanation failed: %s", e)
    positive_count = 0
    negative_count = 0
    if explanation_record and isinstance(explanation_record.get("signal_contribution_overview"), list):
        for item in explanation_record.get("signal_contribution_overview") or []:
            if item.get("contribution") == "positive":
                positive_count += 1
            elif item.get("contribution") == "negative":
                negative_count += 1
    contributing["signal_consistency"] = {"positive": positive_count, "negative": negative_count}
    out["contributing_signals"] = contributing

    # Rule-based confidence score (0–100)
    score = 50  # base
    # Supporting data: up to +15 for multiple data points
    if supporting_data_count >= 5:
        score += 15
    elif supporting_data_count >= 3:
        score += 10
    elif supporting_data_count >= 1:
        score += 5
    # Repeated detections: up to +10
    if repeated_detections >= 5:
        score += 10
    elif repeated_detections >= 2:
        score += 5
    # Lifecycle stability: stable/rising +10, new +5; weakening -5, fading -10
    if lifecycle_state in ("stable", "rising"):
        score += 10
    elif lifecycle_state == "new":
        score += 5
    elif lifecycle_state == "weakening":
        score -= 5
    elif lifecycle_state == "fading":
        score -= 10
    # Trend history: up to +10
    if trend_history_length >= 5:
        score += 10
    elif trend_history_length >= 1:
        score += 5
    # Cluster density: up to +5 (more ASINs = more evidence)
    if cluster_density >= 10:
        score += 5
    elif cluster_density >= 3:
        score += 2
    # Signal consistency: more positive than negative +5, else if more negative -5
    if positive_count > negative_count:
        score += 5
    elif negative_count > positive_count:
        score -= 5
    score = max(0, min(100, score))
    out["confidence_score"] = score

    if score <= SCORE_LOW_MAX:
        out["confidence_label"] = CONFIDENCE_LOW
    elif score <= SCORE_MEDIUM_MAX:
        out["confidence_label"] = CONFIDENCE_MEDIUM
    else:
        out["confidence_label"] = CONFIDENCE_HIGH

    # Compact explanation
    parts: List[str] = []
    parts.append(f"confidence {out['confidence_label']} ({score})")
    if supporting_data_count > 0:
        parts.append(f"supporting_data={supporting_data_count}")
    if repeated_detections > 0:
        parts.append(f"detections={repeated_detections}")
    if lifecycle_state:
        parts.append(f"lifecycle={lifecycle_state}")
    if trend_history_length > 0:
        parts.append(f"trend_history={trend_history_length}")
    if cluster_density > 0:
        parts.append(f"cluster_density={cluster_density}")
    if positive_count or negative_count:
        parts.append(f"signals_positive={positive_count}_negative={negative_count}")
    out["explanation"] = "; ".join(parts)

    return out


def list_opportunities_with_confidence(
    limit: int = 30,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    List opportunity memory entries with confidence scoring for dashboard.
    Returns list of dicts with memory fields plus confidence (opportunity_id, confidence_score, confidence_label, explanation, contributing_signals).
    """
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("list_opportunities_with_confidence list_opportunity_memory failed: %s", e)
        return []
    out: List[Dict[str, Any]] = []
    for mem in rows:
        ref = mem.get("opportunity_ref")
        if not ref:
            continue
        conf = get_opportunity_confidence(ref, workspace_id=workspace_id, memory_record=mem)
        out.append({**mem, "confidence": conf})
    return out
