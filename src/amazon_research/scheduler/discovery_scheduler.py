"""
Step 108: Automated discovery scheduler – schedule and orchestrate category scans, keyword scans,
niche discovery, and opportunity alert evaluation. Compatible with worker queue and delayed jobs.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("scheduler.discovery_scheduler")

TASK_TYPE_CATEGORY_SCAN = "category_scan"
TASK_TYPE_KEYWORD_SCAN = "keyword_scan"
TASK_TYPE_NICHE_DISCOVERY = "niche_discovery"
TASK_TYPE_OPPORTUNITY_ALERT = "opportunity_alert"

# Job types used when enqueueing (must match worker_queue handlers)
JOB_TYPE_CATEGORY_SCAN = "category_scan"
JOB_TYPE_KEYWORD_SCAN = "keyword_scan"
JOB_TYPE_NICHE_DISCOVERY = "niche_discovery"
JOB_TYPE_OPPORTUNITY_ALERT = "opportunity_alert"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def plan_discovery_tasks(
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    max_category_tasks: int = 5,
    max_keyword_tasks: int = 5,
    include_niche_discovery: bool = True,
    include_alert_refresh: bool = True,
) -> Dict[str, Any]:
    """
    Build a discovery schedule from category and keyword scan planners. Returns schedule with
    task_type, target/source, last_run_time (from seed), next_run_time (now or suggested), active.
    Does not enqueue; use enqueue_discovery_schedule to push to worker queue.
    """
    schedule: List[Dict[str, Any]] = []
    now = _now_utc()

    try:
        from amazon_research.planner import build_scan_plan, build_keyword_scan_plan
    except ImportError:
        logger.warning("discovery_scheduler: planners not available")
        return {"schedule": [], "summary": {"total": 0}}

    try:
        cat_plan = build_scan_plan(
            workspace_id=workspace_id,
            marketplace=marketplace,
            max_tasks=max_category_tasks,
        )
    except Exception as e:
        logger.debug("discovery_scheduler: build_scan_plan failed: %s", e)
        cat_plan = {"tasks": []}

    for t in cat_plan.get("tasks") or []:
        schedule.append({
            "task_type": TASK_TYPE_CATEGORY_SCAN,
            "target_source": t.get("category_url") or "",
            "seed_id": t.get("seed_id"),
            "marketplace": t.get("marketplace") or "DE",
            "last_run_time": t.get("last_scanned_at"),
            "next_run_time": now,
            "active": True,
            "payload": {
                "seed_id": t.get("seed_id"),
                "category_url": t.get("category_url"),
                "marketplace": t.get("marketplace") or "DE",
                "label": t.get("label"),
            },
        })

    try:
        kw_plan = build_keyword_scan_plan(
            workspace_id=workspace_id,
            marketplace=marketplace,
            max_tasks=max_keyword_tasks,
        )
    except Exception as e:
        logger.debug("discovery_scheduler: build_keyword_scan_plan failed: %s", e)
        kw_plan = {"tasks": []}

    for t in kw_plan.get("tasks") or []:
        schedule.append({
            "task_type": TASK_TYPE_KEYWORD_SCAN,
            "target_source": t.get("keyword") or "",
            "seed_id": t.get("seed_id"),
            "marketplace": t.get("marketplace") or "DE",
            "last_run_time": t.get("last_scanned_at"),
            "next_run_time": now,
            "active": True,
            "payload": {
                "seed_id": t.get("seed_id"),
                "keyword": t.get("keyword"),
                "marketplace": t.get("marketplace") or "DE",
                "label": t.get("label"),
            },
        })

    if include_niche_discovery:
        schedule.append({
            "task_type": TASK_TYPE_NICHE_DISCOVERY,
            "target_source": "automated",
            "seed_id": None,
            "marketplace": marketplace or "DE",
            "last_run_time": None,
            "next_run_time": now,
            "active": True,
            "payload": {"workspace_id": workspace_id, "marketplace": marketplace},
        })

    if include_alert_refresh:
        schedule.append({
            "task_type": TASK_TYPE_OPPORTUNITY_ALERT,
            "target_source": "board",
            "seed_id": None,
            "marketplace": None,
            "last_run_time": None,
            "next_run_time": now,
            "active": True,
            "payload": {"workspace_id": workspace_id},
        })

    by_type: Dict[str, int] = {}
    for s in schedule:
        t = s.get("task_type") or ""
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "schedule": schedule,
        "summary": {"total": len(schedule), "by_type": by_type},
    }


def enqueue_discovery_schedule(
    plan: Optional[Dict[str, Any]] = None,
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    max_category_tasks: int = 5,
    max_keyword_tasks: int = 5,
    include_niche_discovery: bool = True,
    include_alert_refresh: bool = True,
    scheduled_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Build discovery plan (if plan not provided) and enqueue each task as a worker job.
    Returns job_ids by task_type and summary. Uses existing enqueue_job; job types must be
    handled by worker (category_scan, keyword_scan, niche_discovery, opportunity_alert).
    """
    if plan is None:
        plan = plan_discovery_tasks(
            workspace_id=workspace_id,
            marketplace=marketplace,
            max_category_tasks=max_category_tasks,
            max_keyword_tasks=max_keyword_tasks,
            include_niche_discovery=include_niche_discovery,
            include_alert_refresh=include_alert_refresh,
        )

    schedule = plan.get("schedule") or []
    job_ids: List[int] = []
    job_type_used: Dict[str, int] = {}

    try:
        from amazon_research.db import enqueue_job
    except ImportError:
        logger.warning("discovery_scheduler: enqueue_job not available")
        return {"job_ids": [], "summary": {"enqueued": 0}}

    for item in schedule:
        task_type = item.get("task_type") or ""
        payload = item.get("payload") or {}
        if workspace_id is not None and "workspace_id" not in payload:
            payload = {**payload, "workspace_id": workspace_id}

        jtype = task_type  # category_scan, keyword_scan, niche_discovery, opportunity_alert
        jid = enqueue_job(
            job_type=jtype,
            workspace_id=workspace_id,
            payload=payload,
            scheduled_at=scheduled_at,
        )
        job_ids.append(jid)
        job_type_used[jtype] = job_type_used.get(jtype, 0) + 1

    return {
        "job_ids": job_ids,
        "summary": {"enqueued": len(job_ids), "by_type": job_type_used},
    }
