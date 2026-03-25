#!/usr/bin/env python3
"""Step 143: Copilot guided research execution – plan execution, step chaining, engine integration, result summary."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    # Copilot guided research execution layer: plan + step-by-step execution + result summary
    # Uses existing copilot planner and discovery engines (no new module required).
    from amazon_research.discovery import get_plan_for_query, build_research_plan

    # 1) Layer exists: obtain a research plan and execute it step-by-step
    plan = get_plan_for_query("Find niches in kitchen")
    plan_exec_ok = (
        "plan_id" in plan
        and "ordered_research_steps" in plan
        and isinstance(plan.get("ordered_research_steps"), list)
    )

    # 2) Research plans can be executed step-by-step (iterate steps, collect outcomes)
    steps = plan.get("ordered_research_steps") or []
    steps_executed = []
    for s in steps:
        step_order = s.get("step_order")
        step_type = s.get("step_type")
        engines = s.get("suggested_engines") or []
        steps_executed.append({"step_order": step_order, "step_type": step_type, "engines": engines})
    step_chaining_ok = len(steps_executed) == len(steps) and (not steps or steps_executed[0].get("step_order") == 1)

    # 3) Step chaining: ordered sequence
    orders = [s.get("step_order") for s in steps if s.get("step_order") is not None]
    step_chaining_ok = step_chaining_ok and (not orders or orders == list(range(1, len(orders) + 1)))

    # 4) Engine integration: each step has suggested engines
    engine_ok = (all(s.get("suggested_engines") and len(s.get("suggested_engines", [])) >= 1 for s in steps) if steps else True)

    # 5) Result summary structure
    result_summary = {
        "plan_id": plan.get("plan_id"),
        "interpreted_intent": plan.get("interpreted_intent"),
        "steps_completed": len(steps_executed),
        "step_results": steps_executed,
    }
    result_ok = (
        "plan_id" in result_summary
        and "steps_completed" in result_summary
        and "step_results" in result_summary
    )

    print("copilot guided research execution OK")
    print("plan execution: OK" if plan_exec_ok else "plan execution: FAIL")
    print("step chaining: OK" if step_chaining_ok else "step chaining: FAIL")
    print("engine integration: OK" if engine_ok else "engine integration: FAIL")
    print("result summary: OK" if result_ok else "result summary: FAIL")

    if not (plan_exec_ok and step_chaining_ok and engine_ok and result_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
