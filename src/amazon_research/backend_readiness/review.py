"""
Step 210: Backend readiness review – aggregate checks, overall status, score, blockers, actions.
Deterministic; never raises.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("backend_readiness.review")

STATUS_READY = "ready"
STATUS_CAUTION = "caution"
STATUS_NOT_READY = "not_ready"
PASS = "pass"
WARNING = "warning"
FAIL = "fail"


def run_backend_readiness_review() -> Dict[str, Any]:
    """
    Run all readiness checks and produce normalized backend readiness output.
    Never raises; on internal error returns minimal safe payload with not_ready.
    """
    logger.info("backend_readiness review start", extra={})
    try:
        from amazon_research.backend_readiness.checks import run_all_checks
        items = run_all_checks()
    except Exception as e:
        logger.warning("backend_readiness readiness review failure: %s", e, extra={"error": str(e)})
        return _minimal_not_ready(str(e))

    passed: List[Dict[str, Any]] = []
    warning_list: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for item in items:
        st = (item.get("status") or "").strip().lower()
        if st == PASS:
            passed.append(item)
        elif st == WARNING:
            warning_list.append(item)
        else:
            failed.append(item)
            if item.get("severity") == "critical":
                logger.warning(
                    "backend_readiness critical check failure check_key=%s",
                    item.get("check_key"),
                    extra={"check_key": item.get("check_key"), "rationale": item.get("rationale")},
                )

    total = len(items)
    pass_count = len(passed)
    readiness_score = round(100.0 * pass_count / total, 1) if total else 0.0

    if failed:
        overall_status = STATUS_NOT_READY
    elif warning_list:
        overall_status = STATUS_CAUTION
    else:
        overall_status = STATUS_READY

    top_blockers: List[str] = []
    for item in failed:
        key = item.get("check_key") or ""
        rationale = item.get("rationale") or "Check failed"
        top_blockers.append(f"{key}: {rationale}"[:120])
    for item in warning_list:
        if item.get("severity") in ("high", "critical"):
            key = item.get("check_key") or ""
            rationale = item.get("rationale") or "Warning"
            top_blockers.append(f"{key}: {rationale}"[:120])
    top_blockers = top_blockers[:10]

    recommended_actions: List[str] = []
    for item in failed:
        act = (item.get("recommended_action") or "").strip()
        if act and act not in recommended_actions:
            recommended_actions.append(act)
    if overall_status == STATUS_CAUTION and not recommended_actions:
        recommended_actions.append("Review warning checks and optional subsystems.")
    if overall_status == STATUS_READY and warning_list:
        recommended_actions.append("Optional: address warning checks for full operational confidence.")
    recommended_actions = recommended_actions[:5]

    subsystem_summary: Dict[str, int] = {
        "total_checks": total,
        "passed": pass_count,
        "warnings": len(warning_list),
        "failed": len(failed),
    }

    notes: List[str] = []
    if failed:
        notes.append("One or more core subsystems failed readiness checks.")
    if warning_list:
        notes.append("Some optional or degraded-path checks reported warnings.")
    if overall_status == STATUS_READY:
        notes.append("Backend stack is operationally ready for production-style usage.")
    notes.append("Readiness does not cover external dependencies (e.g. DB connectivity) or load tests.")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "readiness_score": readiness_score,
        "passed_checks": passed,
        "warning_checks": warning_list,
        "failed_checks": failed,
        "subsystem_summary": subsystem_summary,
        "top_blockers": top_blockers,
        "recommended_actions": recommended_actions,
        "notes": notes,
    }
    logger.info(
        "backend_readiness review success overall_status=%s score=%s",
        overall_status, readiness_score,
        extra={"overall_status": overall_status, "readiness_score": readiness_score},
    )
    return out


def _minimal_not_ready(reason: str = "review_failed") -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": STATUS_NOT_READY,
        "readiness_score": 0.0,
        "passed_checks": [],
        "warning_checks": [],
        "failed_checks": [{"check_key": "review_internal", "check_label": "Readiness review", "status": FAIL, "severity": "high", "rationale": reason, "evidence": "", "recommended_action": "Check backend_readiness module and dependencies."}],
        "subsystem_summary": {"total_checks": 0, "passed": 0, "warnings": 0, "failed": 1},
        "top_blockers": [f"review_internal: {reason}"[:120]],
        "recommended_actions": ["Resolve readiness review internal error."],
        "notes": ["Readiness review encountered an internal error; backend status unknown."],
    }
