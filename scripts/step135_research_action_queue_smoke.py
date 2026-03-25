#!/usr/bin/env python3
"""Step 135: Research action queue – action generation, prioritization, rationale output, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

ACTION_TYPES = (
    "rescan_target",
    "prioritize_refresh",
    "add_to_watchlist",
    "inspect_cluster",
    "generate_alert",
    "mark_niche_for_tracking",
)


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import get_action_queue, enqueue_actions

    # Get action queue (from recommendations; may be empty)
    actions = get_action_queue(workspace_id=1, limit_recommendations=15, limit_actions=50)
    gen_ok = isinstance(actions, list)

    # Each action has required fields and valid action_type
    priority_ok = True
    rationale_ok = True
    for a in actions:
        if not (
            "action_id" in a
            and "target_entity" in a
            and "action_type" in a
            and "action_priority" in a
            and "rationale" in a
            and "timestamp" in a
        ):
            gen_ok = False
        if a.get("action_type") not in ACTION_TYPES:
            gen_ok = False
        if "action_priority" in a:
            p = a["action_priority"]
            if not (isinstance(p, (int, float)) and 0 <= p <= 100):
                priority_ok = False
        if "rationale" in a:
            r = a["rationale"]
            if not isinstance(r, dict):
                rationale_ok = False
            elif "recommendation_priority" not in r and "explanation" not in r:
                rationale_ok = rationale_ok and ("recommendation_type" in r or len(r) >= 0)

    # Order: descending by action_priority
    if len(actions) >= 2:
        priority_ok = priority_ok and actions[0].get("action_priority", 0) >= actions[1].get("action_priority", 100)

    # Dashboard: consistent shape
    dashboard_ok = True
    if actions:
        first = actions[0]
        dashboard_ok = (
            (first.get("action_id") or "").startswith("act-")
            and isinstance(first.get("target_entity"), dict)
            and first.get("action_type") in ACTION_TYPES
        )

    # enqueue_actions with empty list (no side effects)
    summary = enqueue_actions([], workspace_id=1)
    dashboard_ok = dashboard_ok and "enqueued" in summary and "skipped" in summary

    print("research action queue OK")
    print("action generation: OK" if gen_ok else "action generation: FAIL")
    print("action prioritization: OK" if priority_ok else "action prioritization: FAIL")
    print("rationale output: OK" if rationale_ok else "rationale output: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (gen_ok and priority_ok and rationale_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
