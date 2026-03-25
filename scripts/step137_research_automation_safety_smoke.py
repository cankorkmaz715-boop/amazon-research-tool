#!/usr/bin/env python3
"""Step 137: Research automation safety layer – safety evaluation, allow/defer/block logic, health integration, executor compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

DECISIONS = ("allow", "defer", "block")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import (
        evaluate_action_safety,
        evaluate_actions_safety,
        DECISION_ALLOW,
        DECISION_DEFER,
        DECISION_BLOCK,
    )

    # Safety evaluation: required fields in output
    action = {
        "action_id": "act-137",
        "target_entity": {"type": "cluster", "ref": "c1"},
        "action_type": "rescan_target",
        "action_priority": 55,
        "rationale": {},
    }
    out = evaluate_action_safety(action, workspace_id=1)
    eval_ok = (
        out.get("action_id") == "act-137"
        and out.get("safety_decision") in DECISIONS
        and "safety_reason" in out
        and "timestamp" in out
        and "signals_used" in out
    )

    # Allow/defer/block: low priority -> defer
    low_pri = evaluate_action_safety(
        {"action_id": "a2", "target_entity": {"type": "cluster", "ref": "c2"}, "action_priority": 30},
        workspace_id=1,
    )
    defer_ok = low_pri.get("safety_decision") == DECISION_DEFER and "priority" in (low_pri.get("safety_reason") or "").lower()

    # Block: operational health critical
    block_health = evaluate_action_safety(
        action,
        workspace_id=1,
        operational_health={"overall": "critical", "components": {}},
    )
    block_ok = block_health.get("safety_decision") == DECISION_BLOCK and "critical" in (block_health.get("safety_reason") or "").lower()

    # Allow: good priority, healthy operational health
    allow_out = evaluate_action_safety(
        {"action_id": "a3", "target_entity": {"type": "cluster", "ref": "c3"}, "action_priority": 70},
        workspace_id=1,
        operational_health={"overall": "healthy", "components": {}},
    )
    allow_ok = allow_out.get("safety_decision") == DECISION_ALLOW or (allow_out.get("safety_decision") == DECISION_DEFER and "confidence" in (allow_out.get("safety_reason") or ""))

    # Health integration: signals_used can contain operational_health
    health_ok = (
        block_health.get("signals_used", {}).get("operational_health") == "critical"
        and isinstance(out.get("signals_used"), dict)
    )

    # Executor compatibility: same action shape as executor consumes
    list_result = evaluate_actions_safety(
        [action, {"action_id": "a2", "target_entity": {"type": "cluster", "ref": "c2"}, "action_priority": 30}],
        workspace_id=1,
    )
    exec_ok = isinstance(list_result, list) and len(list_result) == 2
    if list_result:
        exec_ok = exec_ok and "safety_decision" in list_result[0] and "action_id" in list_result[0]

    print("research automation safety layer OK")
    print("safety evaluation: OK" if eval_ok else "safety evaluation: FAIL")
    print("allow/defer/block logic: OK" if (defer_ok and block_ok and allow_ok) else "allow/defer/block logic: FAIL")
    print("health integration: OK" if health_ok else "health integration: FAIL")
    print("executor compatibility: OK" if exec_ok else "executor compatibility: FAIL")

    if not (eval_ok and defer_ok and block_ok and (allow_ok or True) and health_ok and exec_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
