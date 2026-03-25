"""
Step 207: Crash-safe execution wrapper – lock, timeout, retry, health.
Single entry point for stabilized job execution.
"""
from typing import Any, Callable, Dict, Optional, TypeVar

from amazon_research.logging_config import get_logger

logger = get_logger("worker_stability.runner")

T = TypeVar("T")


def _job_timeout_seconds() -> int:
    try:
        from amazon_research.worker_stability.policy import get_job_timeout_seconds
        return get_job_timeout_seconds()
    except Exception:
        return 600


def execute_with_stability(
    fn: Callable[[], T],
    workspace_id: Optional[int] = None,
    job_type: str = "job",
    timeout_seconds: Optional[int] = None,
    retry_max: Optional[int] = None,
    use_lock: bool = True,
    use_timeout: bool = True,
    use_retry: bool = True,
) -> Dict[str, Any]:
    """
    Run fn() with optional lock, timeout, and retry. Never crashes caller.
    Returns {"ok": True, "result": ...} or {"ok": False, "error": str, "skipped": bool, ...}.
    - use_lock: try acquire (workspace_id, job_type); if not acquired return skipped.
    - use_timeout: run fn with timeout_seconds.
    - use_retry: on failure retry with backoff up to retry_max.
    """
    job_type = (job_type or "job").strip()
    lock_id: Optional[str] = None
    try:
        from amazon_research.worker_stability.health import record_start, record_end, would_starve, record_retry
        if would_starve():
            logger.warning(
                "worker_stability queue safety fallback max active reached workspace_id=%s job_type=%s",
                workspace_id, job_type,
                extra={"workspace_id": workspace_id, "job_type": job_type},
            )
            return {"ok": False, "skipped": True, "error": "max_active_jobs", "reason": "queue_starvation_protection"}
    except Exception as e:
        logger.debug("worker_stability health check skip: %s", e)

    try:
        from amazon_research.resource_guard import check_resource_guard, ALLOW, DEFER, SKIP
        decision, reason, _ = check_resource_guard(workspace_id=workspace_id, job_type=job_type)
        if decision == DEFER:
            return {"ok": False, "skipped": True, "error": reason or "defer", "reason": "resource_guard_defer"}
        if decision == SKIP:
            return {"ok": False, "skipped": True, "error": reason or "skip", "reason": "resource_guard_skip"}
    except Exception as e:
        logger.debug("resource_guard check skip: %s", e)

    if use_lock:
        try:
            from amazon_research.worker_stability.lock import try_acquire, release
            acquired, lock_id = try_acquire(workspace_id, job_type)
            if not acquired:
                return {"ok": False, "skipped": True, "error": "locked", "reason": "duplicate_job_suppression"}
        except Exception as e:
            logger.warning("worker_stability lock acquire failed: %s", e)
            return {"ok": False, "skipped": True, "error": str(e)}

    try:
        from amazon_research.worker_stability.health import record_start, record_end, record_retry
        record_start(workspace_id, job_type)
    except Exception:
        pass
    try:
        from amazon_research.resource_guard import is_heavy_job_type, record_heavy_job_start
        if is_heavy_job_type(job_type):
            record_heavy_job_start(workspace_id, job_type)
    except Exception:
        pass

    try:
        timeout_sec = timeout_seconds if timeout_seconds is not None else _job_timeout_seconds()
        if use_retry:
            from amazon_research.worker_stability.retry import run_with_retry
            def _run() -> T:
                if use_timeout:
                    from amazon_research.worker_stability.timeout import run_with_timeout
                    return run_with_timeout(fn, timeout_sec, workspace_id=workspace_id, job_type=job_type)
                return fn()
            out = run_with_retry(
                _run,
                workspace_id=workspace_id,
                job_type=job_type,
                max_attempts=retry_max,
            )
            if out.get("ok"):
                result = out.get("result")
            else:
                result = None
        else:
            if use_timeout:
                from amazon_research.worker_stability.timeout import run_with_timeout
                result = run_with_timeout(fn, timeout_sec, workspace_id=workspace_id, job_type=job_type)
            else:
                result = fn()
            out = {"ok": True, "result": result}
    except TimeoutError as e:
        logger.warning("worker_stability job timeout in runner workspace_id=%s job_type=%s: %s", workspace_id, job_type, e)
        out = {"ok": False, "error": str(e), "timeout": True}
    except Exception as e:
        logger.exception("worker_stability runner exception workspace_id=%s job_type=%s", workspace_id, job_type)
        out = {"ok": False, "error": str(e)}
    finally:
        try:
            from amazon_research.worker_stability.health import record_end
            record_end(workspace_id, job_type)
        except Exception:
            pass
        try:
            from amazon_research.resource_guard import is_heavy_job_type, record_heavy_job_end
            if is_heavy_job_type(job_type):
                record_heavy_job_end(workspace_id, job_type)
        except Exception:
            pass
        if use_lock and lock_id is not None:
            try:
                from amazon_research.worker_stability.lock import release
                release(workspace_id, job_type, lock_id)
            except Exception as e:
                from amazon_research.worker_stability.lock import release_force
                release_force(workspace_id, job_type)
                logger.warning("worker_stability lock release fallback: %s", e)
    return out
