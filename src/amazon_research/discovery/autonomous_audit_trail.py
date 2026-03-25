"""
Step 139: Autonomous research audit trail – record key decisions and actions from controlled autonomous runs.
Structured, history-friendly. Answers: what the system did, why, what it skipped/blocked.
Integrates with controlled autonomous mode, safety layer, action queue, executor, opportunity memory.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.autonomous_audit_trail")


def _build_audit_payload(run_output: Dict[str, Any]) -> Dict[str, Any]:
    """Build payload for audit: run_id, trigger events, actions considered/executed/deferred/blocked, safety decisions, opportunity outputs, timestamps."""
    payload = dict(run_output)
    # Ensure key fields for audit queries
    payload.setdefault("run_id", "")
    payload.setdefault("actions_considered", 0)
    payload.setdefault("actions_executed", 0)
    payload.setdefault("actions_deferred", 0)
    payload.setdefault("actions_blocked", 0)
    payload.setdefault("execution_results", [])
    payload.setdefault("safety_results", [])
    payload.setdefault("opportunities_summary", {})
    payload.setdefault("timestamp", "")
    return payload


def record_run(run_output: Dict[str, Any]) -> Optional[int]:
    """
    Record one autonomous run in the audit trail. run_output should be the return value of
    run_controlled_autonomous_cycle (run_id, actions_considered, actions_executed, actions_deferred,
    actions_blocked, execution_results, safety_results, opportunities_summary, timestamp).
    Returns audit record id or None.
    """
    run_id = (run_output.get("run_id") or "").strip()
    if not run_id:
        return None
    workspace_id = run_output.get("workspace_id")
    payload = _build_audit_payload(run_output)
    try:
        from amazon_research.db import save_autonomous_run_audit
        return save_autonomous_run_audit(run_id, payload, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("record_run failed: %s", e)
        return None


def get_audit_for_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Return the audit record for the given run_id (id, run_id, workspace_id, payload, created_at)."""
    try:
        from amazon_research.db.autonomous_research_audit import get_audit_for_run as _get
        return _get(run_id)
    except ImportError:
        from amazon_research.db import get_audit_for_run as _get
        return _get(run_id)
    except Exception as e:
        logger.debug("get_audit_for_run failed: %s", e)
        return None


def get_audit_trail(
    workspace_id: Optional[int] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return audit records newest first. Optional workspace_id filter. History-compatible."""
    try:
        from amazon_research.db.autonomous_research_audit import get_audit_trail as _get_trail
        return _get_trail(workspace_id=workspace_id, limit=limit)
    except ImportError:
        from amazon_research.db import get_autonomous_audit_trail
        return get_autonomous_audit_trail(workspace_id=workspace_id, limit=limit)
    except Exception as e:
        logger.debug("get_audit_trail failed: %s", e)
        return []
