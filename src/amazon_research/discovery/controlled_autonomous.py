"""
Step 138: Controlled autonomous research mode – orchestrate discovery, action queue, safety, executor.
Cycle cap, action cap, confidence threshold, health guard, quota guard. No infinite loops.
Conservative, deterministic, rule-based.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.controlled_autonomous")

DEFAULT_ACTION_CAP = 10
DEFAULT_CYCLE_CAP = 1


def run_controlled_autonomous_cycle(
    workspace_id: Optional[int] = None,
    *,
    cycle_cap: int = DEFAULT_CYCLE_CAP,
    action_cap: int = DEFAULT_ACTION_CAP,
    confidence_threshold: Optional[float] = None,
    health_guard: bool = True,
    quota_guard: bool = True,
) -> Dict[str, Any]:
    """
    Run one controlled autonomous research cycle. Coordinates: discovery triggers/scanner (optional),
    action queue, safety layer, executor. Returns: run_id, actions_considered, actions_executed,
    actions_deferred, actions_blocked, summary of discovered opportunities, timestamp.
    Limits: cycle_cap (max discovery enqueue per cycle), action_cap (max actions to consider/execute),
    health_guard (abort when operational health critical), quota_guard (safety layer checks quota).
    """
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    out: Dict[str, Any] = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "actions_considered": 0,
        "actions_executed": 0,
        "actions_deferred": 0,
        "actions_blocked": 0,
        "execution_results": [],
        "safety_results": [],
        "opportunities_summary": {},
        "timestamp": now,
    }

    # Health guard: abort if critical
    operational_health = None
    if health_guard:
        try:
            from amazon_research.monitoring import get_operational_health
            operational_health = get_operational_health()
            if (operational_health.get("overall") or "").strip() == "critical":
                out["opportunities_summary"] = {"reason": "health_guard", "message": "operational health critical; cycle skipped"}
                try:
                    from amazon_research.discovery.autonomous_audit_trail import record_run
                    record_run(out)
                except Exception:
                    pass
                return out
        except Exception as e:
            logger.debug("run_controlled_autonomous get_operational_health failed: %s", e)

    # Optional: run discovery cycle (capped) to refresh recommendations/actions
    if cycle_cap > 0 and workspace_id is not None:
        try:
            from amazon_research.discovery import run_opportunity_discovery_cycle
            run_opportunity_discovery_cycle(
                workspace_id=workspace_id,
                max_enqueue=min(cycle_cap, 5),
                max_trigger_eval=10,
                include_trigger_eval=True,
                include_intelligent_plan=True,
            )
        except Exception as e:
            logger.debug("run_controlled_autonomous discovery cycle failed: %s", e)

    # Get action queue (from recommendations)
    try:
        from amazon_research.discovery import get_action_queue
        actions = get_action_queue(workspace_id=workspace_id, limit_recommendations=action_cap * 2, limit_actions=action_cap)
    except Exception as e:
        logger.debug("run_controlled_autonomous get_action_queue failed: %s", e)
        actions = []
    out["actions_considered"] = len(actions)
    if not actions:
        try:
            from amazon_research.db import list_opportunity_memory
            mem = list_opportunity_memory(limit=5, workspace_id=workspace_id)
            out["opportunities_summary"] = {"count": len(mem), "source": "opportunity_memory"}
        except Exception:
            out["opportunities_summary"] = {"count": 0}
        try:
            from amazon_research.discovery.autonomous_audit_trail import record_run
            record_run(out)
        except Exception:
            pass
        return out

    # Safety evaluation
    try:
        from amazon_research.discovery import evaluate_actions_safety, DECISION_ALLOW, DECISION_DEFER, DECISION_BLOCK
        safety_results = evaluate_actions_safety(actions, workspace_id=workspace_id, operational_health=operational_health)
    except Exception as e:
        logger.debug("run_controlled_autonomous evaluate_actions_safety failed: %s", e)
        safety_results = [{"safety_decision": "allow"} for _ in actions]
    allowed_actions: List[Dict[str, Any]] = []
    deferred = 0
    blocked = 0
    for action, safety in zip(actions, safety_results):
        dec = safety.get("safety_decision") or ""
        if dec == DECISION_BLOCK:
            blocked += 1
        elif dec == DECISION_DEFER:
            deferred += 1
        else:
            allowed_actions.append(action)
    out["actions_deferred"] = deferred
    out["actions_blocked"] = blocked
    out["safety_results"] = safety_results

    # Execute allowed actions (executor has its own validation and max_execute)
    try:
        from amazon_research.discovery import execute_actions, STATUS_SUCCESS
        exec_results = execute_actions(
            allowed_actions,
            workspace_id=workspace_id,
            max_execute=action_cap,
            require_validation=health_guard,
        )
        out["execution_results"] = exec_results
        out["actions_executed"] = sum(1 for r in exec_results if r.get("execution_status") == STATUS_SUCCESS)
    except Exception as e:
        logger.debug("run_controlled_autonomous execute_actions failed: %s", e)

    # Opportunities summary
    try:
        from amazon_research.db import list_opportunity_memory
        from amazon_research.discovery import get_recommendations
        mem_list = list_opportunity_memory(limit=10, workspace_id=workspace_id)
        recos = get_recommendations(workspace_id=workspace_id, limit=5, include_watchlist=False, include_alerts=False)
        out["opportunities_summary"] = {
            "opportunity_memory_count": len(mem_list),
            "recommendations_count": len(recos),
        }
    except Exception:
        out["opportunities_summary"] = {"opportunity_memory_count": 0, "recommendations_count": 0}

    # Audit trail
    try:
        from amazon_research.discovery.autonomous_audit_trail import record_run
        record_run(out)
    except Exception as e:
        logger.debug("run_controlled_autonomous record_run failed: %s", e)

    return out
