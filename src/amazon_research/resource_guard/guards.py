"""
Step 208: Resource guard checks – allow / defer / skip before expensive execution.
Lightweight; never raises; integrates memory pressure and heavy job budget.
"""
from typing import Any, Dict, Optional, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("resource_guard.guards")

ALLOW = "allow"
DEFER = "defer"
SKIP = "skip"


def check_resource_guard(
    workspace_id: Optional[int] = None,
    job_type: Optional[str] = None,
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """
    Run resource guard check before expensive job. Returns (decision, reason, metrics).
    decision: "allow" | "defer" | "skip"
    reason: None if allow, else short reason string.
    metrics: dict with memory_mb, heavy_count, etc. for logging.
    Never raises; on metric read failure uses policy fallback (allow or skip).
    """
    job_type = (job_type or "").strip()
    metrics: Dict[str, Any] = {"memory_mb": None, "heavy_job_count": None, "max_heavy_jobs": None}

    logger.info(
        "resource_guard check start workspace_id=%s job_type=%s",
        workspace_id, job_type,
        extra={"workspace_id": workspace_id, "job_type": job_type},
    )

    try:
        from amazon_research.resource_guard.policy import (
            get_memory_mb_threshold,
            get_defer_enabled,
            get_metric_failure_action,
        )
        from amazon_research.resource_guard.memory_guard import get_process_memory_mb
        from amazon_research.resource_guard.budget import get_heavy_job_count, would_exceed_heavy_budget, is_heavy_job_type
    except Exception as e:
        logger.warning("resource_guard policy import failure: %s", e)
        return ALLOW, None, metrics

    try:
        memory_mb = get_process_memory_mb()
    except Exception as e:
        logger.warning("resource_guard metric read failure memory: %s", e)
        memory_mb = None

    metrics["memory_mb"] = memory_mb
    threshold_mb = get_memory_mb_threshold()
    defer_ok = get_defer_enabled()
    failure_action = get_metric_failure_action()

    if memory_mb is None:
        logger.warning(
            "resource_guard metric read failure; using fallback action=%s workspace_id=%s job_type=%s",
            failure_action, workspace_id, job_type,
            extra={"workspace_id": workspace_id, "job_type": job_type},
        )
        if failure_action == "skip":
            return SKIP, "metrics_unavailable", metrics
        return ALLOW, None, metrics

    if memory_mb >= threshold_mb:
        decision = DEFER if defer_ok else SKIP
        reason = "memory_pressure"
        metrics["memory_threshold_mb"] = threshold_mb
        logger.warning(
            "resource_guard %s memory_pressure workspace_id=%s job_type=%s memory_mb=%s threshold_mb=%s",
            decision, workspace_id, job_type, memory_mb, threshold_mb,
            extra={"workspace_id": workspace_id, "job_type": job_type, "memory_mb": memory_mb, "reason": reason},
        )
        return decision, reason, metrics

    try:
        from amazon_research.resource_guard.budget import get_heavy_job_count, would_exceed_heavy_budget, is_heavy_job_type
        from amazon_research.resource_guard.policy import get_max_heavy_jobs
        heavy_count = get_heavy_job_count()
        max_heavy = get_max_heavy_jobs()
        metrics["heavy_job_count"] = heavy_count
        metrics["max_heavy_jobs"] = max_heavy
    except Exception:
        heavy_count = 0
        max_heavy = 10
        metrics["heavy_job_count"] = heavy_count
        metrics["max_heavy_jobs"] = max_heavy

    if is_heavy_job_type(job_type) and would_exceed_heavy_budget():
        decision = DEFER if defer_ok else SKIP
        reason = "heavy_job_budget_exceeded"
        logger.warning(
            "resource_guard heavy job budget exceeded workspace_id=%s job_type=%s count=%s max=%s",
            workspace_id, job_type, heavy_count, max_heavy,
            extra={"workspace_id": workspace_id, "job_type": job_type, "heavy_job_count": heavy_count, "reason": reason},
        )
        return decision, reason, metrics

    logger.info(
        "resource_guard allow workspace_id=%s job_type=%s memory_mb=%s",
        workspace_id, job_type, memory_mb,
        extra={"workspace_id": workspace_id, "job_type": job_type, "memory_mb": memory_mb},
    )
    return ALLOW, None, metrics
