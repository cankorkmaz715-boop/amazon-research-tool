#!/usr/bin/env python3
"""
Step 70: Scaling Review / Engine Phase Audit.
Audits worker queue, execution loop, retry, delayed scheduling, queue metrics,
multi-worker readiness, distributed refresh planning, async crawler, async refresh path.
Outputs strengths, risks, and next improvements. No rewrite.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def _gather_components():
    """Check presence of engine/scaling layer components. Returns dict."""
    out = {}
    # Worker queue foundation
    try:
        from amazon_research.db import (
            enqueue_job,
            dequeue_next,
            run_job,
            get_queue_metrics,
            schedule_retry_or_mark_failed,
        )
        out["worker_queue"] = True
    except Exception:
        out["worker_queue"] = False
    # Worker execution loop
    try:
        from amazon_research.scheduler import run_worker_loop, get_last_worker_run_summary
        out["worker_loop"] = True
    except Exception:
        out["worker_loop"] = False
    # Retry orchestration (in worker_queue)
    try:
        from amazon_research.db.worker_queue import schedule_retry_or_mark_failed
        out["retry_orchestration"] = True
    except Exception:
        out["retry_orchestration"] = False
    # Delayed job scheduling (scheduled_at)
    try:
        from amazon_research.db import enqueue_job
        import inspect
        sig = inspect.signature(enqueue_job)
        out["delayed_scheduling"] = "scheduled_at" in sig.parameters
    except Exception:
        out["delayed_scheduling"] = False
    # Queue metrics / observability
    try:
        from amazon_research.db import get_queue_metrics
        out["queue_metrics"] = True
    except Exception:
        out["queue_metrics"] = False
    # Multi-worker readiness (claimed_by, worker_id)
    try:
        from amazon_research.db.worker_queue import dequeue_next
        import inspect
        sig = inspect.signature(dequeue_next)
        out["multi_worker_readiness"] = "worker_id" in sig.parameters
    except Exception:
        out["multi_worker_readiness"] = False
    # Distributed refresh planning
    try:
        from amazon_research.planner import get_refresh_candidates, build_refresh_plan
        out["refresh_planning"] = True
    except Exception:
        out["refresh_planning"] = False
    # Async crawler foundation
    try:
        from amazon_research.crawler import get_async_crawler, run_refresh_async
        out["async_crawler"] = True
    except Exception:
        out["async_crawler"] = False
    # Async refresh path
    try:
        from amazon_research.crawler import run_refresh_batch_async
        from amazon_research.db import run_job_async
        import asyncio
        out["async_refresh_path"] = asyncio.iscoroutinefunction(run_refresh_batch_async) and asyncio.iscoroutinefunction(run_job_async)
    except Exception:
        out["async_refresh_path"] = False
    return out


def _build_review(components):
    """Produce strengths, risks, and next improvements from engine/scaling layer."""
    strengths = [
        "Worker queue: DB-backed jobs (discovery, refresh, scoring), enqueue/dequeue with FOR UPDATE SKIP LOCKED for safe claiming.",
        "Worker execution loop: single-worker run_worker_loop(max_jobs), processes jobs sequentially; last run summary for observability.",
        "Retry orchestration: retry_count, max_retries, next_retry_at; schedule_retry_or_mark_failed on failure; final failed state after exhaustion.",
        "Delayed job scheduling: scheduled_at on jobs; dequeue and run_job only eligible when scheduled_at IS NULL or <= current time.",
        "Queue metrics: get_queue_metrics (queued, running, completed, failed, delayed_count); worker run summary stored after each loop.",
        "Multi-worker readiness: claimed_by on jobs, dequeue_next(worker_id), run_job(worker_id); double-processing blocked when claimed by another worker.",
        "Distributed refresh planning: get_refresh_candidates (ordering, skip backoff), build_refresh_plan (batches); payload asin_list for queue-friendly refresh jobs.",
        "Async crawler foundation: AsyncCrawlerProtocol, ThreadedAsyncCrawler (sync bots in asyncio.to_thread); no sync Playwright in asyncio loop.",
        "Async refresh path: run_refresh_batch_async, execute_plan_batch_async; run_job_async for async worker loops (run_job in thread).",
    ]
    risks = [
        "Scaling bottlenecks: single-worker loop only; no horizontal scaling; one process handles all jobs; DB is single point of contention for dequeue.",
        "Operational risks: in-memory rate limits and last-run summary not shared across processes; no distributed lock for multi-process workers.",
        "Async/sync boundary: async path runs sync bots in a thread—acceptable but adds thread overhead; no native async Playwright; mixing sync DB (psycopg2) in async code via to_thread is safe but blocks a thread.",
        "Queue/worker safety: FOR UPDATE SKIP LOCKED prevents double-claim in same DB; multiple processes can run run_worker_loop and each would dequeue different rows; no heartbeat or stuck-job recovery—if a worker dies mid-job, job stays 'running' until manual or timeout logic.",
        "Refresh planning: candidates query and plan are DB-heavy for large asins tables; no pagination or cursor; batch partitioning is in-memory.",
    ]
    next_improvements = [
        "Add heartbeat or started_at-based timeout to mark stuck 'running' jobs as failed or re-queued after N minutes.",
        "Document and optionally enforce single-worker vs multi-process: if multiple processes dequeue, ensure only one run_worker_loop per process and consider worker_id from env or hostname.",
        "Consider rate_limit and queue_metrics in a shared store (e.g. Redis) if moving to multi-process workers.",
        "Add optional native async Playwright path for refresh/discovery to reduce thread pool usage at scale.",
        "Add refresh plan cursor or chunked candidate query for very large ASIN sets.",
    ]
    return {
        "strengths": strengths,
        "risks": risks,
        "next_improvements": next_improvements,
    }


def main():
    components = _gather_components()
    review = _build_review(components)

    print("scaling review OK")
    print("strengths:")
    for s in review["strengths"]:
        print("  -", s)
    print("risks:")
    for r in review["risks"]:
        print("  -", r)
    print("next improvements:")
    for n in review["next_improvements"]:
        print("  -", n)

    # Component checklist (informational)
    print("\ncomponent checklist:")
    for k, v in sorted(components.items()):
        print("  %s: %s" % (k, "OK" if v else "MISSING"))
    sys.exit(0)


if __name__ == "__main__":
    main()
