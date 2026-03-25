"""
Step 127: Opportunity explainability layer – explain why an opportunity candidate is promising.
Aggregates demand, competition, trend, opportunity index, niche scoring, lifecycle. Rule-based, human-readable.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_explainability")


def get_opportunity_explanation(
    opportunity_ref: str,
    *,
    workspace_id: Optional[int] = None,
    memory_record: Optional[Dict[str, Any]] = None,
    lifecycle_record: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Aggregate signals behind opportunity scoring and produce a structured explanation.
    Returns: opportunity_id, main_supporting_signals, explanation_summary, signal_contribution_overview.
    """
    ref = (opportunity_ref or "").strip()
    out: Dict[str, Any] = {
        "opportunity_id": ref,
        "main_supporting_signals": {},
        "explanation_summary": "",
        "signal_contribution_overview": [],
    }
    if not ref:
        out["explanation_summary"] = "Missing opportunity reference."
        return out

    mem = memory_record
    if mem is None:
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
        except Exception as e:
            logger.debug("get_opportunity_explanation get_opportunity_memory failed: %s", e)
    if workspace_id is not None and mem and mem.get("workspace_id") is not None and mem.get("workspace_id") != workspace_id:
        mem = None

    lifecycle = lifecycle_record
    if lifecycle is None:
        try:
            from amazon_research.discovery.opportunity_lifecycle import get_opportunity_lifecycle
            lifecycle = get_opportunity_lifecycle(ref, memory_record=mem)
        except Exception as e:
            logger.debug("get_opportunity_explanation get_opportunity_lifecycle failed: %s", e)
            lifecycle = {}

    trend_data: Optional[Dict[str, Any]] = None
    try:
        from amazon_research.db import get_trend_result_latest
        trend_data = get_trend_result_latest("cluster", ref)
    except Exception as e:
        logger.debug("get_opportunity_explanation get_trend_result_latest failed: %s", e)

    # Build main_supporting_signals from memory context, memory scores, lifecycle, trend
    ctx = (mem or {}).get("context") or {}
    demand = _float(ctx.get("demand_score"))
    competition = _float(ctx.get("competition_score"))
    opportunity_index = _float((mem or {}).get("latest_opportunity_score"))
    if opportunity_index is None and mem:
        opportunity_index = _float(mem.get("latest_opportunity_score"))
    label = ctx.get("label")
    if label is None and isinstance((mem or {}).get("context"), dict):
        label = ((mem or {}).get("context") or {}).get("label")
    label = str(label).strip() if label else ""

    trend_score: Optional[float] = None
    trend_label: Optional[str] = None
    if trend_data and isinstance(trend_data.get("signals"), dict):
        sig = trend_data.get("signals") or {}
        # Prefer a composite or rank trend if present
        for key in ("rank", "trend_score", "composite", "price"):
            v = sig.get(key)
            if isinstance(v, dict) and v.get("trend"):
                trend_label = str(v.get("trend"))
                break
            if isinstance(v, (int, float)):
                trend_score = float(v)
                break
        if trend_label is None and sig:
            trend_label = "available"

    lifecycle_state = (lifecycle or {}).get("lifecycle_state") or ""
    score_trend = (lifecycle or {}).get("supporting_signals") or {}
    if isinstance(score_trend, dict):
        score_trend = score_trend.get("score_trend") or ""

    out["main_supporting_signals"] = {
        "demand_score": demand,
        "competition_score": competition,
        "opportunity_index": opportunity_index,
        "trend_score": trend_score,
        "trend_signal": trend_label,
        "niche_label": label or ref,
        "lifecycle_state": lifecycle_state or "unknown",
        "score_trend": score_trend,
        "memory_status": (mem or {}).get("status") or "",
    }

    # signal_contribution_overview: list of { signal, value, contribution } (positive / neutral / negative)
    overview: List[Dict[str, str]] = []
    _add_contribution(overview, "demand", demand, high_good=True)
    _add_contribution(overview, "competition", competition, high_good=False)
    _add_contribution(overview, "opportunity_index", opportunity_index, high_good=True)
    if trend_score is not None:
        _add_contribution(overview, "trend", trend_score, high_good=True, is_numeric=True)
    else:
        overview.append({"signal": "trend", "value": str(trend_label) if trend_label else "—", "contribution": "neutral"})
    _add_contribution(overview, "lifecycle", lifecycle_state, high_good=True, favorable_values=("rising", "stable", "new"))
    _add_contribution(overview, "score_trend", score_trend, high_good=True, favorable_values=("up",))
    out["signal_contribution_overview"] = overview

    # Short human-readable summary
    parts: List[str] = []
    if opportunity_index is not None:
        parts.append(f"Opportunity index {opportunity_index:.0f}")
    if demand is not None:
        parts.append(f"demand {demand:.0f}")
    if competition is not None:
        parts.append(f"competition {competition:.0f}")
    if lifecycle_state:
        parts.append(f"lifecycle {lifecycle_state}")
    if score_trend:
        parts.append(f"score trend {score_trend}")
    if trend_label:
        parts.append(f"trend {trend_label}")
    out["explanation_summary"] = ". ".join(parts) if parts else "No signals available for this opportunity."

    return out


def _float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _add_contribution(
    overview: List[Dict[str, str]],
    signal: str,
    value: Any,
    *,
    high_good: bool = True,
    is_numeric: bool = True,
    favorable_values: Optional[tuple] = None,
) -> None:
    entry: Dict[str, str] = {"signal": signal, "value": str(value) if value is not None else "—", "contribution": "neutral"}
    if value is None and signal != "trend":
        overview.append(entry)
        return
    if is_numeric and isinstance(value, (int, float)):
        v = float(value)
        if high_good:
            entry["contribution"] = "positive" if v >= 50 else ("negative" if v < 30 else "neutral")
        else:
            entry["contribution"] = "positive" if v <= 50 else ("negative" if v > 70 else "neutral")
    elif favorable_values and value in favorable_values:
        entry["contribution"] = "positive"
    elif signal in ("lifecycle", "score_trend") and value:
        entry["contribution"] = "neutral"
    overview.append(entry)


def list_explanations(
    limit: int = 20,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    List opportunity explanations for dashboard/replay. Uses opportunity memory list then enriches with get_opportunity_explanation.
    Returns list of full explanation dicts (opportunity_id, main_supporting_signals, explanation_summary, signal_contribution_overview).
    """
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("list_explanations list_opportunity_memory failed: %s", e)
        return []
    out: List[Dict[str, Any]] = []
    for m in rows:
        ref = m.get("opportunity_ref")
        if not ref:
            continue
        out.append(get_opportunity_explanation(ref, workspace_id=workspace_id, memory_record=m))
    return out
