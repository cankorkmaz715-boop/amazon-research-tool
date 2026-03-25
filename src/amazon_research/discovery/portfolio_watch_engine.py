"""
Step 131: Portfolio watch engine – monitor ASIN, keyword, niche, cluster over time.
Uses opportunity memory, lifecycle, explainability, trend. Produces watch outputs for change detection.
Lightweight, rule-based. Alert-engine compatible.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.portfolio_watch_engine")

CHANGE_OPPORTUNITY_SCORE = "opportunity_score_change"
CHANGE_LIFECYCLE = "lifecycle_change"
CHANGE_TREND = "trend_change"
CHANGE_DEMAND = "demand_change"
CHANGE_COMPETITION = "competition_change"
CHANGE_NEW_DATA = "new_data"
CHANGE_NONE = "no_change"


def _current_snapshot_for_entity(
    target_type: str,
    target_ref: str,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Build current state snapshot from memory, lifecycle, explainability, trend (where applicable)."""
    snap: Dict[str, Any] = {
        "opportunity_score": None,
        "lifecycle_state": None,
        "trend_score": None,
        "demand_score": None,
        "competition_score": None,
    }
    ref = (target_ref or "").strip()
    if not ref:
        return snap
    # Cluster/niche: use opportunity_ref = cluster_id; memory, lifecycle, explainability, trend
    mem: Optional[Dict[str, Any]] = None
    if target_type in ("cluster", "niche"):
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
            if mem:
                snap["opportunity_score"] = mem.get("latest_opportunity_score")
                ctx = mem.get("context") or {}
                snap["demand_score"] = ctx.get("demand_score")
                snap["competition_score"] = ctx.get("competition_score")
        except Exception as e:
            logger.debug("portfolio_watch get_opportunity_memory failed: %s", e)
        try:
            from amazon_research.discovery.opportunity_lifecycle import get_opportunity_lifecycle
            life = get_opportunity_lifecycle(ref, memory_record=mem)
            if life:
                snap["lifecycle_state"] = life.get("lifecycle_state")
        except Exception as e:
            logger.debug("portfolio_watch get_opportunity_lifecycle failed: %s", e)
        try:
            from amazon_research.discovery.opportunity_explainability import get_opportunity_explanation
            expl = get_opportunity_explanation(ref, workspace_id=workspace_id)
            if expl:
                sigs = expl.get("main_supporting_signals") or {}
                if snap.get("demand_score") is None:
                    snap["demand_score"] = sigs.get("demand_score")
                if snap.get("competition_score") is None:
                    snap["competition_score"] = sigs.get("competition_score")
                if snap.get("opportunity_score") is None:
                    snap["opportunity_score"] = sigs.get("opportunity_index")
                snap["trend_score"] = sigs.get("trend_score") or sigs.get("trend_signal")
        except Exception as e:
            logger.debug("portfolio_watch get_opportunity_explanation failed: %s", e)
        try:
            from amazon_research.db import get_trend_result_latest
            trend = get_trend_result_latest("cluster", ref)
            if trend and trend.get("signals"):
                snap["trend_score"] = snap.get("trend_score") or trend.get("signals")
        except Exception as e:
            logger.debug("portfolio_watch get_trend_result_latest failed: %s", e)
    # ASIN: trend results
    if target_type == "asin":
        try:
            from amazon_research.db import get_trend_result_latest
            trend = get_trend_result_latest("asin", ref)
            if trend:
                snap["trend_score"] = trend.get("signals")
        except Exception as e:
            logger.debug("portfolio_watch get_trend_result_latest asin failed: %s", e)
    # Keyword: discovery results only (no opportunity score); optional placeholder
    if target_type == "keyword":
        try:
            from amazon_research.db import get_discovery_result_latest
            dr = get_discovery_result_latest("keyword", ref)
            if dr:
                snap["new_data"] = len(dr.get("asins") or [])
        except Exception as e:
            logger.debug("portfolio_watch get_discovery_result_latest failed: %s", e)
    return snap


def _detect_change_type(last: Dict[str, Any], current: Dict[str, Any]) -> tuple:
    """Rule-based: return (change_type, supporting_signal_summary)."""
    summary: Dict[str, Any] = {}
    if not last or not last.keys():
        return CHANGE_NEW_DATA, {"current": current}
    changes: List[str] = []
    o_old = last.get("opportunity_score")
    o_new = current.get("opportunity_score")
    if o_old is not None and o_new is not None and float(o_old) != float(o_new):
        changes.append(CHANGE_OPPORTUNITY_SCORE)
        summary["opportunity_score_previous"] = o_old
        summary["opportunity_score_current"] = o_new
    l_old = last.get("lifecycle_state")
    l_new = current.get("lifecycle_state")
    if l_old != l_new and (l_old or l_new):
        changes.append(CHANGE_LIFECYCLE)
        summary["lifecycle_previous"] = l_old
        summary["lifecycle_current"] = l_new
    t_old = last.get("trend_score")
    t_new = current.get("trend_score")
    if t_old != t_new and (t_old is not None or t_new is not None):
        changes.append(CHANGE_TREND)
        summary["trend_previous"] = t_old
        summary["trend_current"] = t_new
    d_old = last.get("demand_score")
    d_new = current.get("demand_score")
    if d_old is not None and d_new is not None and float(d_old) != float(d_new):
        changes.append(CHANGE_DEMAND)
        summary["demand_previous"] = d_old
        summary["demand_current"] = d_new
    c_old = last.get("competition_score")
    c_new = current.get("competition_score")
    if c_old is not None and c_new is not None and float(c_old) != float(c_new):
        changes.append(CHANGE_COMPETITION)
        summary["competition_previous"] = c_old
        summary["competition_current"] = c_new
    if not changes:
        return CHANGE_NONE, {"current": current}
    return changes[0] if len(changes) == 1 else CHANGE_OPPORTUNITY_SCORE, summary


def evaluate_watch(
    watch_id: int,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Evaluate one watch: build current snapshot, compare to last_snapshot, produce watch output.
    Returns: watch_id, watched_entity (type + ref), detected_change_type, supporting_signal_summary, timestamp.
    Updates last_snapshot in DB after evaluation.
    """
    from amazon_research.db import get_watch, update_watch_snapshot
    watch = get_watch(watch_id, workspace_id=workspace_id) if workspace_id is not None else get_watch(watch_id)
    out: Dict[str, Any] = {
        "watch_id": watch_id,
        "watched_entity": {"type": "", "ref": ""},
        "detected_change_type": CHANGE_NONE,
        "supporting_signal_summary": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if not watch:
        return out
    ttype = watch.get("target_type") or "cluster"
    ref = watch.get("target_ref") or ""
    out["watched_entity"] = {"type": ttype, "ref": ref}
    last = watch.get("last_snapshot") or {}
    current = _current_snapshot_for_entity(ttype, ref, workspace_id=workspace_id or watch.get("workspace_id"))
    change_type, summary = _detect_change_type(last, current)
    out["detected_change_type"] = change_type
    out["supporting_signal_summary"] = summary
    update_watch_snapshot(watch_id, current, workspace_id=workspace_id or watch.get("workspace_id"))
    return out


def evaluate_all_watches(
    workspace_id: int,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Evaluate all watches for the workspace. Returns list of watch outputs (watch_id, watched_entity, ...)."""
    from amazon_research.db import list_watches
    watches = list_watches(workspace_id, limit=limit)
    results: List[Dict[str, Any]] = []
    for w in watches:
        wid = w.get("id")
        if wid is None:
            continue
        results.append(evaluate_watch(wid, workspace_id=workspace_id))
    return results


def register_watch(
    workspace_id: int,
    target_type: str,
    target_ref: str,
) -> Optional[int]:
    """Register a watch. target_type: asin | keyword | niche | cluster. Returns watch id or None."""
    from amazon_research.db import add_watch
    return add_watch(workspace_id, target_type, target_ref)
