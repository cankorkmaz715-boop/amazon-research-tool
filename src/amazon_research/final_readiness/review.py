"""
Step 230: Final production readiness review – full-system evaluation (backend, frontend, operational).
Aggregates backend readiness + final-specific checks. Deterministic; never raises.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("final_readiness.review")

STATUS_READY = "ready"
STATUS_CAUTION = "caution"
STATUS_NOT_READY = "not_ready"
PASS = "pass"
WARNING = "warning"
FAIL = "fail"


def run_final_readiness_review() -> Dict[str, Any]:
    """
    Run backend readiness review plus final-specific checks. Merge results and produce
    final payload. Never raises; on internal error returns minimal safe payload.
    """
    logger.info("final_readiness review start", extra={})
    try:
        backend = _run_backend_review()
        final_items = _run_final_checks()
    except Exception as e:
        logger.warning("final_readiness review failure: %s", e, extra={"error": str(e)})
        return _minimal_not_ready(str(e))

    # Merge checks: backend passed/warning/failed + final passed/warning/failed
    passed: List[Dict[str, Any]] = list(backend.get("passed_checks") or [])
    warning_list: List[Dict[str, Any]] = list(backend.get("warning_checks") or [])
    failed: List[Dict[str, Any]] = list(backend.get("failed_checks") or [])

    for item in final_items:
        st = (item.get("status") or "").strip().lower()
        if st == PASS:
            passed.append(item)
        elif st == WARNING:
            warning_list.append(item)
        else:
            failed.append(item)

    total = len(passed) + len(warning_list) + len(failed)
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

    recommended_next_actions: List[str] = []
    for item in failed:
        act = (item.get("recommended_action") or "").strip()
        if act and act not in recommended_next_actions:
            recommended_next_actions.append(act)
    if overall_status == STATUS_CAUTION and not recommended_next_actions:
        recommended_next_actions.append("Review warning checks and optional subsystems.")
    if overall_status == STATUS_READY and warning_list:
        recommended_next_actions.append("Optional: address warning checks for full confidence.")
    recommended_next_actions = recommended_next_actions[:5]

    subsystem_summary: Dict[str, Any] = {
        "total_checks": total,
        "passed": pass_count,
        "warnings": len(warning_list),
        "failed": len(failed),
        "backend_status": backend.get("overall_status"),
        "backend_score": backend.get("readiness_score"),
    }

    notes: List[str] = []
    if failed:
        notes.append("One or more checks failed; review top_blockers and recommended_next_actions.")
    if warning_list:
        notes.append("Some checks reported warnings; system may be usable with limitations.")
    if overall_status == STATUS_READY:
        notes.append("Full-system production readiness review passed; suitable for controlled real-world usage.")
    notes.append("Review covers backend, frontend structure, deployment hardening, and operational wiring; not load or security audit.")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "readiness_score": readiness_score,
        "passed_checks": passed,
        "warning_checks": warning_list,
        "failed_checks": failed,
        "subsystem_summary": subsystem_summary,
        "top_blockers": top_blockers,
        "recommended_next_actions": recommended_next_actions,
        "notes": notes,
    }
    logger.info(
        "final_readiness review success overall_status=%s score=%s",
        overall_status, readiness_score,
        extra={"overall_status": overall_status, "readiness_score": readiness_score},
    )
    return out


def _run_backend_review() -> Dict[str, Any]:
    try:
        from amazon_research.backend_readiness import run_backend_readiness_review
        return run_backend_readiness_review()
    except Exception as e:
        return {
            "passed_checks": [],
            "warning_checks": [],
            "failed_checks": [{"check_key": "backend_review", "status": FAIL, "rationale": str(e)[:200], "severity": "high"}],
            "overall_status": STATUS_NOT_READY,
            "readiness_score": 0.0,
        }


def _run_final_checks() -> List[Dict[str, Any]]:
    try:
        from amazon_research.final_readiness.checks import run_final_checks as run_
        return run_()
    except Exception as e:
        return [{
            "check_key": "final_checks",
            "check_label": "Final checks",
            "status": FAIL,
            "severity": "medium",
            "rationale": str(e)[:200],
            "evidence": "exception",
            "recommended_action": "Verify final_readiness.checks module.",
        }]


def _minimal_not_ready(reason: str = "review_failed") -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": STATUS_NOT_READY,
        "readiness_score": 0.0,
        "passed_checks": [],
        "warning_checks": [],
        "failed_checks": [{"check_key": "review_internal", "check_label": "Final readiness review", "status": FAIL, "severity": "high", "rationale": reason, "evidence": "", "recommended_action": "Check final_readiness module and dependencies."}],
        "subsystem_summary": {"total_checks": 0, "passed": 0, "warnings": 0, "failed": 1, "backend_status": None, "backend_score": None},
        "top_blockers": [f"review_internal: {reason}"[:120]],
        "recommended_next_actions": ["Resolve final readiness review internal error."],
        "notes": ["Final readiness review encountered an internal error."],
    }
