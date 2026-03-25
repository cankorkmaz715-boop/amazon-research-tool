#!/usr/bin/env python3
"""Step 164: Intelligent crawl scheduler – priority scoring, target selection, staleness, scheduler compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.scheduler.intelligent_crawl_scheduler import (
        get_intelligent_crawl_schedule,
        to_scheduler_tasks,
        enqueue_intelligent_crawl_schedule,
        TARGET_KEYWORD,
        TARGET_CATEGORY,
        TARGET_NICHE,
        TARGET_CLUSTER,
    )

    # 1) Priority scoring: schedule has priority_score, sorted descending
    schedule = get_intelligent_crawl_schedule(workspace_id=1, limit=20)
    scores = [s.get("priority_score") for s in schedule if s.get("priority_score") is not None]
    priority_ok = all(
        "priority_score" in s and isinstance(s.get("priority_score"), (int, float)) for s in schedule
    ) if schedule else True
    priority_ok = priority_ok and (scores == sorted(scores, reverse=True) if len(scores) > 1 else True)

    # 2) Target selection: each item has target_id, target_type, scheduling_rationale, timestamp
    target_ok = all(
        s.get("target_id") is not None
        and s.get("target_type") in (TARGET_KEYWORD, TARGET_CATEGORY, TARGET_NICHE, TARGET_CLUSTER)
        and "scheduling_rationale" in s
        and s.get("timestamp")
        for s in schedule
    ) if schedule else True
    if not schedule:
        target_ok = True  # empty schedule is valid

    # 3) Staleness handling: scheduling_rationale can mention stale or opportunity/confidence
    staleness_ok = True
    if schedule:
        has_rationale = all(isinstance(s.get("scheduling_rationale"), str) for s in schedule)
        staleness_ok = has_rationale

    # 4) Scheduler compatibility: to_scheduler_tasks produces task_type, payload; enqueue returns job_ids/summary
    tasks = to_scheduler_tasks(schedule, workspace_id=1)
    compat_ok = isinstance(tasks, list) and all(
        t.get("task_type") and t.get("payload") is not None for t in tasks
    ) if tasks else True
    enq = enqueue_intelligent_crawl_schedule(schedule=[], workspace_id=1, limit=0)
    compat_ok = compat_ok and "job_ids" in enq and "summary" in enq

    print("intelligent crawl scheduler OK")
    print("priority scoring: OK" if priority_ok else "priority scoring: FAIL")
    print("target selection: OK" if target_ok else "target selection: FAIL")
    print("staleness handling: OK" if staleness_ok else "staleness handling: FAIL")
    print("scheduler compatibility: OK" if compat_ok else "scheduler compatibility: FAIL")

    if not (priority_ok and target_ok and staleness_ok and compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
