"""
Step 136: Semi-automated research executor – process actions from the research action queue.
Validates actions (priority, confidence, lifecycle, operational health) then executes via
worker queue, watchlist, alert engine. Rule-based, safe, capped. No uncontrolled autonomous execution.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.research_executor")

STATUS_SUCCESS = "success"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

# Safety: minimum action priority to execute; do not execute when operational health is critical
MIN_PRIORITY_TO_EXECUTE = 40
DEFAULT_MAX_EXECUTE = 10


def validate_action(
    action: Dict[str, Any],
    workspace_id: Optional[int] = None,
    *,
    min_priority: float = MIN_PRIORITY_TO_EXECUTE,
    operational_health: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate an action before execution. Returns: valid (bool), reason (str), signals_used (dict).
    Checks: action_priority >= min_priority; optional operational health (skip if critical);
    optional confidence/lifecycle for cluster/niche refs.
    """
    out: Dict[str, Any] = {"valid": False, "reason": "", "signals_used": {}}
    priority = action.get("action_priority")
    try:
        priority = float(priority) if priority is not None else 0.0
    except (TypeError, ValueError):
        priority = 0.0
    out["signals_used"]["action_priority"] = priority
    if priority < min_priority:
        out["reason"] = f"action_priority {priority} below minimum {min_priority}"
        return out
    entity = action.get("target_entity") or {}
    ref = (entity.get("ref") or "").strip()
    if not ref:
        out["reason"] = "missing target_entity.ref"
        return out
    if operational_health is not None:
        overall = (operational_health.get("overall") or "").strip()
        out["signals_used"]["operational_health"] = overall
        if overall == "critical":
            out["reason"] = "operational health critical; execution withheld"
            return out
    etype = (entity.get("type") or "cluster").strip()
    if etype in ("cluster", "niche") and ref:
        try:
            from amazon_research.discovery import get_opportunity_confidence, get_opportunity_lifecycle
            conf = get_opportunity_confidence(ref, workspace_id=workspace_id)
            life = get_opportunity_lifecycle(ref)
            out["signals_used"]["confidence_score"] = conf.get("confidence_score")
            out["signals_used"]["lifecycle_state"] = life.get("lifecycle_state")
        except Exception as e:
            logger.debug("validate_action confidence/lifecycle failed: %s", e)
    out["valid"] = True
    out["reason"] = "validated"
    return out


def execute_action(
    action: Dict[str, Any],
    workspace_id: Optional[int] = None,
    *,
    skip_validation: bool = False,
    operational_health: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute one action. If skip_validation is False, validates first; if invalid returns status skipped.
    Returns: execution_id, processed_action_id, execution_status (success|skipped|failed),
    execution_summary, timestamp.
    """
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"
    action_id = action.get("action_id") or ""
    now = datetime.now(timezone.utc).isoformat()
    out: Dict[str, Any] = {
        "execution_id": execution_id,
        "processed_action_id": action_id,
        "execution_status": STATUS_SKIPPED,
        "execution_summary": "",
        "timestamp": now,
    }
    if not skip_validation:
        val = validate_action(action, workspace_id, operational_health=operational_health)
        if not val.get("valid"):
            out["execution_summary"] = val.get("reason") or "validation failed"
            return out
    entity = action.get("target_entity") or {}
    ref = (entity.get("ref") or "").strip()
    etype = (entity.get("type") or "cluster").strip()
    atype = (action.get("action_type") or "").strip()
    try:
        if atype == "rescan_target":
            from amazon_research.db import enqueue_job
            jid = enqueue_job(
                job_type="niche_discovery",
                workspace_id=workspace_id,
                payload={"cluster_id": ref, "scope": "rescan"},
            )
            if jid:
                out["execution_status"] = STATUS_SUCCESS
                out["execution_summary"] = f"enqueued niche_discovery job {jid} for {ref}"
            else:
                out["execution_status"] = STATUS_FAILED
                out["execution_summary"] = "enqueue_job returned None"
        elif atype == "prioritize_refresh":
            from amazon_research.db import enqueue_job
            jid = enqueue_job(
                job_type="niche_discovery",
                workspace_id=workspace_id,
                payload={"cluster_id": ref, "scope": "refresh"},
            )
            if jid:
                out["execution_status"] = STATUS_SUCCESS
                out["execution_summary"] = f"enqueued refresh job {jid} for {ref}"
            else:
                out["execution_status"] = STATUS_FAILED
                out["execution_summary"] = "enqueue returned None"
        elif atype in ("add_to_watchlist", "mark_niche_for_tracking") and workspace_id is not None:
            from amazon_research.db import add_watch
            watch_type = "niche" if etype == "niche" else "cluster"
            wid = add_watch(workspace_id, watch_type, ref)
            if wid:
                out["execution_status"] = STATUS_SUCCESS
                out["execution_summary"] = f"registered watch {wid} for {ref}"
            else:
                out["execution_status"] = STATUS_FAILED
                out["execution_summary"] = "add_watch returned None"
        elif atype == "generate_alert":
            from amazon_research.db import save_opportunity_alert
            alert = {
                "target_entity": ref,
                "target_type": etype,
                "alert_type": "executor_generated",
                "triggering_signals": action.get("rationale") or {},
            }
            aid = save_opportunity_alert(alert, workspace_id=workspace_id)
            if aid:
                out["execution_status"] = STATUS_SUCCESS
                out["execution_summary"] = f"saved opportunity alert {aid} for {ref}"
            else:
                out["execution_status"] = STATUS_FAILED
                out["execution_summary"] = "save_opportunity_alert returned None"
        elif atype == "inspect_cluster":
            from amazon_research.db import enqueue_job
            jid = enqueue_job(
                job_type="niche_discovery",
                workspace_id=workspace_id,
                payload={"cluster_id": ref, "scope": "inspect"},
            )
            if jid:
                out["execution_status"] = STATUS_SUCCESS
                out["execution_summary"] = f"scheduled cluster inspection job {jid} for {ref}"
            else:
                out["execution_status"] = STATUS_FAILED
                out["execution_summary"] = "enqueue returned None"
        else:
            out["execution_summary"] = f"unsupported action_type {atype}"
    except Exception as e:
        logger.debug("execute_action failed: %s", e)
        out["execution_status"] = STATUS_FAILED
        out["execution_summary"] = str(e)
    return out


def execute_actions(
    actions: List[Dict[str, Any]],
    workspace_id: Optional[int] = None,
    *,
    max_execute: int = DEFAULT_MAX_EXECUTE,
    require_validation: bool = True,
) -> List[Dict[str, Any]]:
    """
    Process actions from the research action queue. Validates each (unless require_validation=False),
    then executes up to max_execute actions. Returns list of execution results (execution_id,
    processed_action_id, execution_status, execution_summary, timestamp). Safe: no uncontrolled loop.
    """
    health: Optional[Dict[str, Any]] = None
    if require_validation:
        try:
            from amazon_research.monitoring import get_operational_health
            health = get_operational_health()
        except Exception as e:
            logger.debug("execute_actions get_operational_health failed: %s", e)
    results: List[Dict[str, Any]] = []
    executed = 0
    for action in actions:
        if executed >= max_execute:
            break
        res = execute_action(
            action,
            workspace_id=workspace_id,
            skip_validation=not require_validation,
            operational_health=health,
        )
        results.append(res)
        if res.get("execution_status") == STATUS_SUCCESS:
            executed += 1
    return results
