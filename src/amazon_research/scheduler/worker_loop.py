"""
Worker execution loop v1. Step 62 – process queued jobs sequentially; single-worker, lightweight.
Reuses queue foundation (dequeue_next, run_job). Status: pending -> running -> completed|failed.
Step 65: last run summary stored for observability.
"""
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger
from amazon_research.db import dequeue_next, run_job

logger = get_logger("scheduler.worker_loop")

_last_run_summary: Optional[Dict[str, Any]] = None


def get_last_worker_run_summary() -> Optional[Dict[str, Any]]:
    """Step 65: Return summary of the last run_worker_loop execution (jobs_processed, jobs_completed, jobs_failed)."""
    return _last_run_summary.copy() if _last_run_summary else None


def run_worker_loop(max_jobs: Optional[int] = None, worker_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process queued jobs sequentially until queue is empty or max_jobs reached.
    Single-worker; no concurrency. Step 66: optional worker_id for safe multi-worker readiness.
    Returns summary: jobs_processed, jobs_completed, jobs_failed.
    """
    summary: Dict[str, Any] = {
        "jobs_processed": 0,
        "jobs_completed": 0,
        "jobs_failed": 0,
    }
    processed = 0
    while True:
        if max_jobs is not None and processed >= max_jobs:
            break
        job = dequeue_next(worker_id=worker_id)
        if not job:
            break
        job_id = job["id"]
        job_type = job.get("job_type", "?")
        logger.info("worker_loop processing job", extra={"job_id": job_id, "job_type": job_type, "worker_id": worker_id})
        result = run_job(job_id, worker_id=worker_id)
        processed += 1
        summary["jobs_processed"] = processed
        if result.get("ok"):
            summary["jobs_completed"] = summary.get("jobs_completed", 0) + 1
        elif result.get("skipped"):
            # Step 64: job not yet eligible (e.g. scheduled_at in future); not a failure
            pass
        else:
            summary["jobs_failed"] = summary.get("jobs_failed", 0) + 1
            logger.warning("worker_loop job failed", extra={"job_id": job_id, "error": result.get("error")})
    global _last_run_summary
    _last_run_summary = summary
    return summary
