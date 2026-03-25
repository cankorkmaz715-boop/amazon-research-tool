#!/usr/bin/env python3
"""Step 149: Copilot comparative research mode – multi-target planning, parallel execution, comparison summary, copilot compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from amazon_research.db import init_db
        init_db()
    except Exception:
        pass

    from amazon_research.discovery import run_comparative_research, compare_targets, interpret_query

    # 1) Multi-target planning: two targets (niche vs niche)
    targets = [
        {"type": "niche", "label": "kitchen"},
        {"type": "niche", "label": "garden"},
    ]
    result = run_comparative_research(targets, workspace_id=1)
    multi_ok = (
        result.get("comparison_id") is not None
        and (result.get("comparison_id") or "").startswith("compare-")
        and len(result.get("targets_compared") or []) == 2
        and len(result.get("summary_metrics_per_target") or []) == 2
    )

    # 2) Parallel research execution: each target has steps_completed / plan
    metrics = result.get("summary_metrics_per_target") or []
    exec_ok = all(
        "steps_completed" in m and "plan_id" in m and (m.get("plan_id") or m.get("steps_completed", 0) >= 0)
        for m in metrics
    )
    if result.get("insights_per_target"):
        exec_ok = exec_ok and len(result["insights_per_target"]) == 2

    # 3) Comparison summary: required fields and suggested best candidate
    summary_ok = (
        "comparative_insight_summary" in result
        and isinstance(result.get("comparative_insight_summary"), str)
        and len(result.get("comparative_insight_summary") or "") > 0
        and "suggested_best_candidate" in result
    )
    best = result.get("suggested_best_candidate") or {}
    summary_ok = summary_ok and "target_index" in best and "rationale" in best and "timestamp" in result

    # 4) Copilot compatibility: uses planner/interpret path; convenience API
    result2 = compare_targets([{"type": "keyword", "label": "blender"}, "Explore supplements"], workspace_id=1)
    copilot_ok = (
        result2.get("comparison_id") is not None
        and len(result2.get("targets_compared") or []) >= 1
        and "summary_metrics_per_target" in result2
    )
    interp = interpret_query("Find niches in kitchen")
    copilot_ok = copilot_ok and interp.get("interpreted_intent") is not None

    print("comparative research mode OK")
    print("multi-target planning: OK" if multi_ok else "multi-target planning: FAIL")
    print("parallel research execution: OK" if exec_ok else "parallel research execution: FAIL")
    print("comparison summary: OK" if summary_ok else "comparison summary: FAIL")
    print("copilot compatibility: OK" if copilot_ok else "copilot compatibility: FAIL")

    if not (multi_ok and exec_ok and summary_ok and copilot_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
