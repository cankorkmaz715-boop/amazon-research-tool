#!/usr/bin/env python3
"""Step 142: Copilot research planner – intent-to-plan, step sequencing, engine suggestion, planning rationale."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import build_research_plan, get_plan_for_query, interpret_query

    # Intent-to-plan: build from copilot output
    copilot_out = interpret_query("Find new niches")
    plan = build_research_plan(copilot_out)
    intent_ok = (
        plan.get("plan_id", "").startswith("plan-")
        and plan.get("interpreted_intent") == "niche_discovery"
        and "ordered_research_steps" in plan
        and "planning_rationale_summary" in plan
        and "timestamp" in plan
    )

    # Step sequencing: ordered steps with step_order, step_type, suggested_engines
    steps = plan.get("ordered_research_steps") or []
    seq_ok = isinstance(steps, list) and len(steps) >= 2
    if steps:
        seq_ok = seq_ok and steps[0].get("step_order") == 1
        seq_ok = seq_ok and "step_type" in steps[0] and "suggested_engines" in steps[0]
        seq_ok = seq_ok and isinstance(steps[0].get("suggested_engines"), list)

    # Engine suggestion per step
    engine_ok = True
    for s in steps:
        if not (s.get("suggested_engines") and len(s.get("suggested_engines", [])) >= 1):
            engine_ok = False
            break

    # Planning rationale: non-empty string
    rationale = plan.get("planning_rationale_summary") or ""
    rationale_ok = isinstance(rationale, str) and len(rationale) > 0

    # get_plan_for_query: full flow
    plan2 = get_plan_for_query("Explore keywords for supplements")
    full_ok = (
        plan2.get("interpreted_intent") == "keyword_exploration"
        and len(plan2.get("ordered_research_steps") or []) >= 2
    )

    print("copilot research planner OK")
    print("intent-to-plan: OK" if intent_ok else "intent-to-plan: FAIL")
    print("step sequencing: OK" if seq_ok else "step sequencing: FAIL")
    print("engine suggestion: OK" if engine_ok else "engine suggestion: FAIL")
    print("planning rationale: OK" if (rationale_ok and full_ok) else "planning rationale: FAIL")

    if not (intent_ok and seq_ok and engine_ok and rationale_ok and full_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
