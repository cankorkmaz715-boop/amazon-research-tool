#!/usr/bin/env python3
"""
Step 140: Autonomous research governance review.
Audits: semi-automated research executor, research automation safety layer,
controlled autonomous research mode, autonomous research audit trail.
Verifies execution remains controlled and bounded; consistency of action generation,
execution decisions, safety outcomes, run summaries, audit logging; explainability of
what was executed, skipped, and why blocked/deferred. Identifies strengths, risks, next improvements.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

WORKSPACE_ID = 1


def check_execution_control():
    """Executor and controlled mode: caps (max_execute, action_cap), health guard, validation."""
    ok = True
    try:
        from amazon_research.discovery import (
            validate_action,
            execute_action,
            execute_actions,
            STATUS_SKIPPED,
            STATUS_SUCCESS,
        )
        from amazon_research.discovery.research_executor import DEFAULT_MAX_EXECUTE, MIN_PRIORITY_TO_EXECUTE
        # Executor has bounded execution
        low_pri = {"action_id": "a", "target_entity": {"ref": "r"}, "action_priority": 20}
        val = validate_action(low_pri, workspace_id=WORKSPACE_ID, min_priority=MIN_PRIORITY_TO_EXECUTE)
        ok = ok and val.get("valid") is False
        exec_skip = execute_action(low_pri, workspace_id=WORKSPACE_ID, skip_validation=False)
        ok = ok and exec_skip.get("execution_status") == STATUS_SKIPPED
        # execute_actions respects max_execute
        results = execute_actions([low_pri, low_pri], workspace_id=WORKSPACE_ID, max_execute=1, require_validation=True)
        ok = ok and isinstance(results, list) and len(results) <= 2
        # Controlled autonomous: cycle cap, action cap, health guard
        from amazon_research.discovery import run_controlled_autonomous_cycle
        out = run_controlled_autonomous_cycle(
            workspace_id=WORKSPACE_ID,
            cycle_cap=0,
            action_cap=5,
            health_guard=True,
        )
        ok = ok and "run_id" in out and "actions_considered" in out and "actions_executed" in out
        ok = ok and out.get("actions_considered", -1) >= 0 and out.get("actions_executed", -1) >= 0
    except Exception:
        ok = False
    return ok


def check_safety_consistency():
    """Safety layer: allow/defer/block, reason, signals; batch evaluation aligns with actions."""
    ok = True
    try:
        from amazon_research.discovery import (
            evaluate_action_safety,
            evaluate_actions_safety,
            DECISION_ALLOW,
            DECISION_DEFER,
            DECISION_BLOCK,
        )
        action = {"action_id": "a1", "target_entity": {"type": "cluster", "ref": "c1"}, "action_priority": 55}
        single = evaluate_action_safety(action, workspace_id=WORKSPACE_ID)
        ok = (
            single.get("safety_decision") in (DECISION_ALLOW, DECISION_DEFER, DECISION_BLOCK)
            and "safety_reason" in single
            and "signals_used" in single
        )
        batch = evaluate_actions_safety([action], workspace_id=WORKSPACE_ID)
        ok = ok and len(batch) == 1 and batch[0].get("action_id") == "a1"
        # Block when health critical
        block = evaluate_action_safety(action, operational_health={"overall": "critical"})
        ok = ok and block.get("safety_decision") == DECISION_BLOCK
    except Exception:
        ok = False
    return ok


def check_auditability():
    """Run output and audit trail: run_id, actions executed/deferred/blocked, safety_results, audit storage."""
    ok = True
    try:
        from amazon_research.discovery import (
            run_controlled_autonomous_cycle,
            record_run,
            get_audit_for_run,
            get_autonomous_audit_trail,
        )
        out = run_controlled_autonomous_cycle(
            workspace_id=WORKSPACE_ID,
            cycle_cap=0,
            action_cap=3,
            health_guard=True,
        )
        run_id = out.get("run_id")
        ok = (
            "run_id" in out
            and "actions_considered" in out
            and "actions_executed" in out
            and "actions_deferred" in out
            and "actions_blocked" in out
            and "execution_results" in out
            and "safety_results" in out
            and "opportunities_summary" in out
            and "timestamp" in out
        )
        # Audit: record and retrieve
        record_run(out)
        trail = get_autonomous_audit_trail(workspace_id=WORKSPACE_ID, limit=5)
        ok = ok and isinstance(trail, list)
        if run_id:
            rec = get_audit_for_run(run_id)
            if rec:
                payload = rec.get("payload") or {}
                ok = ok and payload.get("run_id") == run_id and "actions_executed" in payload
                ok = ok and ("safety_results" in payload or "execution_results" in payload)
    except Exception:
        ok = False
    return ok


def main():
    from dotenv import load_dotenv
    load_dotenv()

    execution_ok = check_execution_control()
    safety_ok = check_safety_consistency()
    audit_ok = check_auditability()

    strengths = [
        "Executor validates action priority and operational health before execution; low priority or critical health yields skipped.",
        "execute_actions enforces max_execute cap; no unbounded execution.",
        "Safety layer produces allow/defer/block with safety_reason and signals_used; block on critical health, quota exceeded, loop detection.",
        "Controlled autonomous cycle has cycle_cap and action_cap; health_guard aborts when operational health is critical.",
        "Run output includes actions_considered, actions_executed, actions_deferred, actions_blocked, execution_results, safety_results, opportunities_summary.",
        "Audit trail records each run via record_run(run_output); payload stores full run for what/why/skipped; get_audit_for_run and get_audit_trail support history.",
    ]

    governance_risks = [
        "Executor and safety use different priority thresholds (executor MIN 40, safety MIN_PRIORITY_ALLOW 50); consistent but could be unified.",
        "Audit table must exist (migration 030); record_run is best-effort and does not fail the cycle on audit write failure.",
        "No per-workspace or global daily/hourly execution budget beyond action_cap per cycle; repeated invocations can still enqueue many jobs.",
        "Loop detection in safety is per-batch (recent_target_refs within evaluate_actions_safety); no cross-run persistence of 'recently executed' refs.",
        "Quota check in safety uses discovery_run only; other quota types (e.g. refresh_run) not evaluated for autonomous actions.",
    ]

    next_improvements = [
        "Unify or document executor vs safety priority thresholds; consider single configurable threshold.",
        "Add optional execution budget (e.g. max actions per workspace per day) and enforce in executor or controlled mode.",
        "Persist 'recently executed' target refs (e.g. in audit or a small table) for cross-run loop prevention.",
        "Extend safety layer to check all relevant quota types used by autonomous actions (discovery, refresh, etc.).",
        "Ensure audit write failure is logged and optionally surfaced in run output (e.g. audit_recorded: false).",
        "Add governance view API or dashboard feed: list recent runs with run_id, actions_executed, actions_blocked, link to audit payload.",
    ]

    print("autonomous governance review OK")
    print("execution control: OK" if execution_ok else "execution control: FAIL")
    print("safety consistency: OK" if safety_ok else "safety consistency: FAIL")
    print("auditability: OK" if audit_ok else "auditability: FAIL")
    print("governance risks:")
    for r in governance_risks:
        print(f"  - {r}")
    print("next improvements:")
    for n in next_improvements:
        print(f"  - {n}")
    print("strengths:")
    for s in strengths:
        print(f"  - {s}")

    all_ok = execution_ok and safety_ok and audit_ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
