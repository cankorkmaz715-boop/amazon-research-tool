"""
Step 135: Research action queue – turn recommendations into structured next actions.
Action types: rescan target, prioritize refresh, add to watchlist, inspect cluster, generate alert,
mark niche for tracking. Lightweight, rule-based, explainable. Integrates with recommendation engine,
watchlist intelligence, alert prioritization, worker queue.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.action_queue")

ACTION_RESCAN_TARGET = "rescan_target"
ACTION_PRIORITIZE_REFRESH = "prioritize_refresh"
ACTION_ADD_TO_WATCHLIST = "add_to_watchlist"
ACTION_INSPECT_CLUSTER = "inspect_cluster"
ACTION_GENERATE_ALERT = "generate_alert"
ACTION_MARK_NICHE_FOR_TRACKING = "mark_niche_for_tracking"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _recommendation_to_actions(rec: Dict[str, Any], workspace_id: Optional[int]) -> List[Dict[str, Any]]:
    """Map one recommendation to one or more actions. Rule-based."""
    actions: List[Dict[str, Any]] = []
    entity = rec.get("target_entity") or {}
    etype = (entity.get("type") or "cluster").strip()
    ref = (entity.get("ref") or "").strip()
    if not ref:
        return actions
    rec_type = (rec.get("recommendation_type") or "").strip()
    priority = float(rec.get("priority_score") or 50.0)
    explanation = rec.get("explanation") or ""
    now = _ts()
    rationale = {"recommendation_priority": priority, "recommendation_type": rec_type, "explanation": explanation}

    # High priority -> rescan + inspect
    if priority >= 60:
        actions.append({
            "action_id": f"act-{uuid.uuid4().hex[:12]}",
            "target_entity": {"type": etype, "ref": ref},
            "action_type": ACTION_RESCAN_TARGET,
            "action_priority": round(priority, 1),
            "rationale": rationale.copy(),
            "timestamp": now,
        })
        actions.append({
            "action_id": f"act-{uuid.uuid4().hex[:12]}",
            "target_entity": {"type": etype, "ref": ref},
            "action_type": ACTION_INSPECT_CLUSTER,
            "action_priority": round(priority - 5, 1),
            "rationale": rationale.copy(),
            "timestamp": now,
        })
    # Watchlist attention -> add to watchlist if not already (we don't check here; downstream can dedupe)
    if rec_type == "watchlist_attention" and workspace_id is not None:
        actions.append({
            "action_id": f"act-{uuid.uuid4().hex[:12]}",
            "target_entity": {"type": etype, "ref": ref},
            "action_type": ACTION_ADD_TO_WATCHLIST,
            "action_priority": round(priority, 1),
            "rationale": rationale.copy(),
            "timestamp": now,
        })
    # Lifecycle rising -> mark niche for tracking
    if rec_type == "lifecycle_rising" and workspace_id is not None:
        actions.append({
            "action_id": f"act-{uuid.uuid4().hex[:12]}",
            "target_entity": {"type": etype, "ref": ref},
            "action_type": ACTION_MARK_NICHE_FOR_TRACKING,
            "action_priority": round(priority, 1),
            "rationale": rationale.copy(),
            "timestamp": now,
        })
    # Alert prioritized -> generate alert
    if rec_type == "alert_prioritized":
        actions.append({
            "action_id": f"act-{uuid.uuid4().hex[:12]}",
            "target_entity": {"type": etype, "ref": ref},
            "action_type": ACTION_GENERATE_ALERT,
            "action_priority": round(priority, 1),
            "rationale": rationale.copy(),
            "timestamp": now,
        })
    # Medium priority without specific type -> inspect only
    if priority >= 45 and priority < 60 and not any(a["action_type"] == ACTION_INSPECT_CLUSTER for a in actions):
        actions.append({
            "action_id": f"act-{uuid.uuid4().hex[:12]}",
            "target_entity": {"type": etype, "ref": ref},
            "action_type": ACTION_INSPECT_CLUSTER,
            "action_priority": round(priority, 1),
            "rationale": rationale.copy(),
            "timestamp": now,
        })
    # Prioritize refresh for high-opportunity clusters
    if rec_type == "high_opportunity" and priority >= 55:
        actions.append({
            "action_id": f"act-{uuid.uuid4().hex[:12]}",
            "target_entity": {"type": etype, "ref": ref},
            "action_type": ACTION_PRIORITIZE_REFRESH,
            "action_priority": round(priority - 3, 1),
            "rationale": rationale.copy(),
            "timestamp": now,
        })
    return actions


def get_action_queue(
    workspace_id: Optional[int] = None,
    *,
    limit_recommendations: int = 30,
    limit_actions: int = 100,
) -> List[Dict[str, Any]]:
    """
    Build research action queue from recommendations. Returns list of actions (action_id, target_entity,
    action_type, action_priority, rationale, timestamp) sorted by action_priority descending.
    """
    try:
        from amazon_research.discovery import get_recommendations
    except Exception as e:
        logger.debug("get_action_queue get_recommendations failed: %s", e)
        return []
    recos = get_recommendations(
        workspace_id=workspace_id,
        limit=limit_recommendations,
        include_watchlist=True,
        include_alerts=True,
    )
    actions: List[Dict[str, Any]] = []
    for rec in recos:
        actions.extend(_recommendation_to_actions(rec, workspace_id))
    actions.sort(key=lambda x: (-(x.get("action_priority") or 0), x.get("timestamp", "")))
    return actions[:limit_actions]


def enqueue_actions(
    actions: List[Dict[str, Any]],
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Optional: enqueue selected actions to worker queue / watchlist. rescan_target -> niche_discovery or
    keyword_scan; add_to_watchlist / mark_niche_for_tracking -> add_watch. Returns summary of enqueued/skipped.
    Does not rewrite worker core; uses existing enqueue_job and add_watch.
    """
    enqueued: List[int] = []
    skipped: List[str] = []
    for act in actions:
        atype = act.get("action_type")
        entity = act.get("target_entity") or {}
        ref = (entity.get("ref") or "").strip()
        etype = (entity.get("type") or "cluster").strip()
        if not ref:
            skipped.append(atype or "unknown")
            continue
        try:
            if atype == ACTION_RESCAN_TARGET:
                from amazon_research.db import enqueue_job
                jid = enqueue_job(
                    job_type="niche_discovery",
                    workspace_id=workspace_id,
                    payload={"cluster_id": ref, "scope": "rescan"},
                )
                if jid:
                    enqueued.append(jid)
            elif atype in (ACTION_ADD_TO_WATCHLIST, ACTION_MARK_NICHE_FOR_TRACKING) and workspace_id is not None:
                from amazon_research.db import add_watch
                wid = add_watch(workspace_id, "niche" if etype == "niche" else "cluster", ref)
                if wid:
                    enqueued.append(wid)
            else:
                skipped.append(atype or "unknown")
        except Exception as e:
            logger.debug("enqueue_actions failed for %s: %s", atype, e)
            skipped.append(atype or "unknown")
    return {"enqueued": enqueued, "skipped": skipped, "count": len(enqueued)}
