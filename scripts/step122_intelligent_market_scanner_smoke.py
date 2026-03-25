#!/usr/bin/env python3
"""Step 122: Intelligent market scanner – signal prioritization, scan planning, scheduler and crawler compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_KEYS = ("scan_target", "target_type", "priority_score", "scan_reason", "timestamp")
VALID_TARGET_TYPES = ("keyword", "category", "niche", "cluster")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import (
        build_intelligent_scan_plan,
        to_scheduler_tasks,
        enqueue_intelligent_plan,
    )

    plan_result = build_intelligent_scan_plan(
        workspace_id=None,
        marketplace="DE",
        max_keywords=3,
        max_categories=3,
        max_niches=3,
        use_triggers=True,
    )

    plans = plan_result.get("scan_plans") or []
    summary = plan_result.get("summary") or {}
    signal_ok = (
        isinstance(plans, list)
        and isinstance(summary, dict)
        and "total" in summary
        and "timestamp" in plan_result
    )
    if plans:
        signal_ok = signal_ok and all(
            (p.get("priority_score") is not None and p.get("target_type") in VALID_TARGET_TYPES)
            for p in plans
        )

    scan_plan_ok = True
    for p in plans[:5]:
        scan_plan_ok = scan_plan_ok and all(k in p for k in REQUIRED_KEYS)
    if not plans:
        scan_plan_ok = plan_result.get("summary", {}).get("total") == 0

    tasks = to_scheduler_tasks(plan_result, workspace_id=None, marketplace="DE")
    scheduler_ok = isinstance(tasks, list)
    for t in tasks:
        scheduler_ok = scheduler_ok and "task_type" in t and "payload" in t
        payload = t.get("payload") or {}
        if t.get("task_type") == "keyword_scan":
            scheduler_ok = scheduler_ok and "keyword" in payload
        elif t.get("task_type") == "category_scan":
            scheduler_ok = scheduler_ok and "category_url" in payload

    crawler_ok = True
    for t in tasks:
        jtype = t.get("task_type") or ""
        crawler_ok = crawler_ok and jtype in ("keyword_scan", "category_scan", "niche_discovery")

    print("intelligent market scanner OK")
    print("signal prioritization: OK" if signal_ok else "signal prioritization: FAIL")
    print("scan planning: OK" if scan_plan_ok else "scan planning: FAIL")
    print("scheduler integration: OK" if scheduler_ok else "scheduler integration: FAIL")
    print("crawler compatibility: OK" if crawler_ok else "crawler compatibility: FAIL")

    if not (signal_ok and scan_plan_ok and scheduler_ok and crawler_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
