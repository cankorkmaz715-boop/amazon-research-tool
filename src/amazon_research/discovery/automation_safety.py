"""
Step 137: Research automation safety layer – evaluate whether queued research actions are safe to execute.
Uses confidence, action priority, lifecycle, operational health, quota, worker/queue health,
repeated action detection. Decisions: allow, defer, block. Rule-based, conservative, explainable.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.automation_safety")

DECISION_ALLOW = "allow"
DECISION_DEFER = "defer"
DECISION_BLOCK = "block"

# Conservative thresholds
MIN_PRIORITY_ALLOW = 50
MIN_CONFIDENCE_ALLOW = 40
QUOTA_TYPE_DISCOVERY = "discovery_run"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate_action_safety(
    action: Dict[str, Any],
    workspace_id: Optional[int] = None,
    *,
    operational_health: Optional[Dict[str, Any]] = None,
    recent_target_refs: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Evaluate whether an action is safe to execute. Returns: action_id, safety_decision (allow|defer|block),
    safety_reason (str), timestamp, signals_used (dict). Conservative: block on critical health or quota;
    defer on warning or low priority/confidence or loop detection.
    """
    action_id = action.get("action_id") or ""
    entity = action.get("target_entity") or {}
    ref = (entity.get("ref") or "").strip()
    priority = action.get("action_priority")
    try:
        priority = float(priority) if priority is not None else 0.0
    except (TypeError, ValueError):
        priority = 0.0
    now = _ts()
    out: Dict[str, Any] = {
        "action_id": action_id,
        "safety_decision": DECISION_ALLOW,
        "safety_reason": "",
        "timestamp": now,
        "signals_used": {"action_priority": priority},
    }
    reasons: List[str] = []

    # Block: operational health critical
    if operational_health is not None:
        overall = (operational_health.get("overall") or "").strip()
        out["signals_used"]["operational_health"] = overall
        if overall == "critical":
            out["safety_decision"] = DECISION_BLOCK
            out["safety_reason"] = "operational health critical"
            return out
        if overall == "warning":
            reasons.append("operational health warning")

    # Block: queue/worker from health components
    if operational_health:
        components = operational_health.get("components") or {}
        qc = components.get("queue") or {}
        wc = components.get("worker") or {}
        if (qc.get("status") or "") == "critical":
            out["safety_decision"] = DECISION_BLOCK
            out["safety_reason"] = "queue health critical"
            return out
        if (wc.get("status") or "") == "critical":
            out["safety_decision"] = DECISION_BLOCK
            out["safety_reason"] = "worker health critical"
            return out
        if (qc.get("status") or "") == "warning":
            reasons.append("queue backlog warning")

    # Block: quota exceeded
    if workspace_id is not None:
        try:
            from amazon_research.db import check_quota
            q = check_quota(workspace_id, QUOTA_TYPE_DISCOVERY)
            out["signals_used"]["quota_allowed"] = q.get("allowed")
            if q.get("allowed") is False and q.get("limit") is not None:
                out["safety_decision"] = DECISION_BLOCK
                out["safety_reason"] = "quota exceeded for discovery_run"
                return out
        except Exception as e:
            logger.debug("evaluate_action_safety check_quota failed: %s", e)

    # Block: repeated action / loop detection (same target ref in recent set)
    recent = recent_target_refs or set()
    if ref and ref in recent:
        out["safety_decision"] = DECISION_BLOCK
        out["safety_reason"] = "repeated action on same target (loop prevention)"
        out["signals_used"]["recent_target_refs"] = True
        return out

    # Defer: low priority
    if priority < MIN_PRIORITY_ALLOW:
        reasons.append(f"action_priority {priority} below {MIN_PRIORITY_ALLOW}")

    # Defer: low confidence for cluster/niche
    etype = (entity.get("type") or "cluster").strip()
    if etype in ("cluster", "niche") and ref:
        try:
            from amazon_research.discovery import get_opportunity_confidence
            conf = get_opportunity_confidence(ref, workspace_id=workspace_id)
            cs = conf.get("confidence_score")
            if cs is not None:
                try:
                    cs = float(cs)
                    out["signals_used"]["confidence_score"] = cs
                    if cs < MIN_CONFIDENCE_ALLOW:
                        reasons.append(f"confidence_score {cs} below {MIN_CONFIDENCE_ALLOW}")
                except (TypeError, ValueError):
                    pass
        except Exception as e:
            logger.debug("evaluate_action_safety get_opportunity_confidence failed: %s", e)

    if reasons:
        out["safety_decision"] = DECISION_DEFER
        out["safety_reason"] = "; ".join(reasons)
    else:
        out["safety_reason"] = "allowed"
    return out


def evaluate_actions_safety(
    actions: List[Dict[str, Any]],
    workspace_id: Optional[int] = None,
    *,
    operational_health: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate safety for a list of actions. Fetches operational health once if not provided.
    For loop detection, treats refs already seen in the same batch as recent (first occurrence allowed, subsequent deferred or blocked).
    """
    if operational_health is None:
        try:
            from amazon_research.monitoring import get_operational_health
            operational_health = get_operational_health()
        except Exception as e:
            logger.debug("evaluate_actions_safety get_operational_health failed: %s", e)
            operational_health = {}
    recent: Set[str] = set()
    results: List[Dict[str, Any]] = []
    for action in actions:
        entity = action.get("target_entity") or {}
        ref = (entity.get("ref") or "").strip()
        res = evaluate_action_safety(
            action,
            workspace_id=workspace_id,
            operational_health=operational_health,
            recent_target_refs=recent.copy(),
        )
        results.append(res)
        if ref and res.get("safety_decision") == DECISION_ALLOW:
            recent.add(ref)
    return results
