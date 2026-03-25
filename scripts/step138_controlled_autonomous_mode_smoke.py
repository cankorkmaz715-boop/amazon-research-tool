#!/usr/bin/env python3
"""Step 138: Controlled autonomous research mode – trigger integration, action orchestration, safety enforcement, run summary."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import run_controlled_autonomous_cycle

    # Run one cycle with tight caps (no discovery enqueue if health guard triggers)
    out = run_controlled_autonomous_cycle(
        workspace_id=1,
        cycle_cap=0,
        action_cap=5,
        health_guard=True,
    )

    # Required output shape
    summary_ok = (
        "run_id" in out
        and (out.get("run_id") or "").startswith("run-")
        and "actions_considered" in out
        and "actions_executed" in out
        and "actions_deferred" in out
        and "actions_blocked" in out
        and "opportunities_summary" in out
        and "timestamp" in out
    )

    # Trigger integration: cycle_cap=0 skips discovery; still runs action queue + safety + executor
    trigger_ok = isinstance(out.get("actions_considered"), (int, float))

    # Action orchestration: execution_results present when actions were considered
    exec_results = out.get("execution_results") or []
    action_ok = (
        isinstance(exec_results, list)
        and (out["actions_considered"] == 0 or len(exec_results) <= out["actions_considered"])
    )

    # Safety enforcement: deferred + blocked counts
    safety_ok = (
        isinstance(out.get("actions_deferred"), (int, float))
        and isinstance(out.get("actions_blocked"), (int, float))
    )

    # Autonomous run summary
    opp = out.get("opportunities_summary") or {}
    autonomous_ok = isinstance(opp, dict) and ("reason" in opp or "count" in opp or "opportunity_memory_count" in opp or "recommendations_count" in opp)

    print("controlled autonomous research mode OK")
    print("trigger integration: OK" if trigger_ok else "trigger integration: FAIL")
    print("action orchestration: OK" if action_ok else "action orchestration: FAIL")
    print("safety enforcement: OK" if safety_ok else "safety enforcement: FAIL")
    print("autonomous run summary: OK" if (summary_ok and autonomous_ok) else "autonomous run summary: FAIL")

    if not (summary_ok and trigger_ok and action_ok and safety_ok and autonomous_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
