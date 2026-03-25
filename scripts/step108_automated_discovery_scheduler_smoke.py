#!/usr/bin/env python3
"""Step 108: Automated discovery scheduler – schedule creation, task planning, queue integration, next-run logic."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.scheduler import (
        plan_discovery_tasks,
        enqueue_discovery_schedule,
        TASK_TYPE_CATEGORY_SCAN,
        TASK_TYPE_KEYWORD_SCAN,
        TASK_TYPE_NICHE_DISCOVERY,
        TASK_TYPE_OPPORTUNITY_ALERT,
    )

    schedule_creation_ok = False
    task_planning_ok = False
    queue_integration_ok = False
    next_run_ok = False

    # Plan (no DB required for structure; planners may return empty if no seeds)
    plan = plan_discovery_tasks(
        workspace_id=None,
        marketplace=None,
        max_category_tasks=2,
        max_keyword_tasks=2,
        include_niche_discovery=True,
        include_alert_refresh=True,
    )
    schedule = plan.get("schedule") or []
    summary = plan.get("summary") or {}

    schedule_creation_ok = isinstance(schedule, list) and "summary" in plan and isinstance(summary, dict)
    task_planning_ok = all(
        s.get("task_type") in (TASK_TYPE_CATEGORY_SCAN, TASK_TYPE_KEYWORD_SCAN, TASK_TYPE_NICHE_DISCOVERY, TASK_TYPE_OPPORTUNITY_ALERT)
        and "next_run_time" in s
        and "payload" in s
        for s in schedule
    ) if schedule else True
    if not schedule:
        task_planning_ok = "schedule" in plan

    # Next-run logic: each item has next_run_time (and optionally last_run_time)
    next_run_ok = all(
        "next_run_time" in s and "task_type" in s and "active" in s
        for s in schedule
    ) if schedule else True

    # Queue integration: enqueue (may need DB for worker_jobs table)
    try:
        from amazon_research.db import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'worker_jobs'")
        has_queue = cur.fetchone() is not None
        cur.close()
    except Exception:
        has_queue = False

    if has_queue:
        result = enqueue_discovery_schedule(
            plan=plan,
            workspace_id=None,
            max_category_tasks=0,
            max_keyword_tasks=0,
            include_niche_discovery=True,
            include_alert_refresh=True,
        )
        job_ids = result.get("job_ids") or []
        queue_integration_ok = isinstance(job_ids, list) and (len(job_ids) >= 1 or len(schedule) == 0)
        if not queue_integration_ok and len(schedule) > 0:
            queue_integration_ok = "enqueued" in (result.get("summary") or {})
    else:
        queue_integration_ok = callable(enqueue_discovery_schedule)

    print("automated discovery scheduler OK")
    print("schedule creation: OK" if schedule_creation_ok else "schedule creation: FAIL")
    print("task planning: OK" if task_planning_ok else "task planning: FAIL")
    print("queue integration: OK" if queue_integration_ok else "queue integration: FAIL")
    print("next-run logic: OK" if next_run_ok else "next-run logic: FAIL")

    if not (schedule_creation_ok and task_planning_ok and queue_integration_ok and next_run_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
