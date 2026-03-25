#!/usr/bin/env python3
"""Step 136: Semi-automated research executor – action validation, execution, scheduler/worker compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import validate_action, execute_action, execute_actions, STATUS_SUCCESS, STATUS_SKIPPED, STATUS_FAILED

    # Validation: low priority -> invalid
    low_priority_action = {
        "action_id": "act-smoke",
        "target_entity": {"type": "cluster", "ref": "c1"},
        "action_type": "rescan_target",
        "action_priority": 20,
        "rationale": {},
    }
    val_low = validate_action(low_priority_action, workspace_id=1, min_priority=40)
    validation_ok = val_low.get("valid") is False and "priority" in (val_low.get("reason") or "").lower()

    # Validation: sufficient priority + ref -> valid
    val_ok = validate_action(
        {"action_id": "act-2", "target_entity": {"type": "cluster", "ref": "c2"}, "action_priority": 55, "rationale": {}},
        workspace_id=1,
        min_priority=40,
    )
    validation_ok = validation_ok and val_ok.get("valid") is True and "signals_used" in val_ok

    # Execute: invalid action -> skipped
    exec_skip = execute_action(low_priority_action, workspace_id=1, skip_validation=False)
    execution_ok = (
        exec_skip.get("execution_status") == STATUS_SKIPPED
        and "execution_id" in exec_skip
        and "processed_action_id" in exec_skip
        and "execution_summary" in exec_skip
        and "timestamp" in exec_skip
    )

    # Execute: valid action (register watch) with skip_validation to avoid DB for rescan
    watch_action = {
        "action_id": "act-watch",
        "target_entity": {"type": "cluster", "ref": "smoke-exec-136"},
        "action_type": "add_to_watchlist",
        "action_priority": 60,
        "rationale": {},
    }
    exec_watch = execute_action(watch_action, workspace_id=1, skip_validation=True)
    execution_ok = (
        execution_ok
        and exec_watch.get("execution_status") in (STATUS_SUCCESS, STATUS_FAILED)
        and (exec_watch.get("execution_id") or "").startswith("exec-")
    )

    # execute_actions: cap and structure
    list_result = execute_actions([low_priority_action, watch_action], workspace_id=1, max_execute=2, require_validation=True)
    scheduler_ok = isinstance(list_result, list) and len(list_result) <= 2
    if list_result:
        scheduler_ok = scheduler_ok and "execution_status" in list_result[0] and "execution_id" in list_result[0]

    # Worker compatibility: execution output shape compatible with dashboard/scheduler
    worker_ok = (
        "execution_id" in exec_skip
        and "processed_action_id" in exec_skip
        and "execution_status" in exec_skip
        and exec_skip.get("execution_status") in (STATUS_SUCCESS, STATUS_SKIPPED, STATUS_FAILED)
    )

    print("research executor OK")
    print("action validation: OK" if validation_ok else "action validation: FAIL")
    print("action execution: OK" if execution_ok else "action execution: FAIL")
    print("scheduler integration: OK" if scheduler_ok else "scheduler integration: FAIL")
    print("worker compatibility: OK" if worker_ok else "worker compatibility: FAIL")

    if not (validation_ok and execution_ok and scheduler_ok and worker_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
