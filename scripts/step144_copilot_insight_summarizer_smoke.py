#!/usr/bin/env python3
"""Step 144: Copilot insight summarizer – insight extraction, signal summary, risk notes, next-step suggestions."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import (
        get_plan_for_query,
        build_insight_summary,
        summarize_guided_execution,
    )

    # 1) Summarizer exists and produces required structure
    plan = get_plan_for_query("Find niches in kitchen")
    steps = plan.get("ordered_research_steps") or []
    step_results = [
        {"step_order": s.get("step_order"), "step_type": s.get("step_type"), "engines": s.get("suggested_engines") or []}
        for s in steps
    ]
    execution_output = {
        "plan_id": plan.get("plan_id"),
        "interpreted_intent": plan.get("interpreted_intent"),
        "steps_completed": len(step_results),
        "step_results": step_results,
    }

    summary = build_insight_summary(execution_output, plan_id=plan.get("plan_id"))

    # Required fields
    has_id = (summary.get("summary_id") or "").startswith("summary-")
    has_target = "target_research_request_id" in summary
    insight_ok = has_id and has_target and "key_insights" in summary and isinstance(summary.get("key_insights"), list)

    # 2) Signal summary
    signals = summary.get("main_supporting_signals") or {}
    signal_ok = isinstance(signals, dict)

    # 3) Risk / uncertainty notes
    risk_notes = summary.get("risk_uncertainty_notes") or []
    risk_ok = isinstance(risk_notes, list)

    # 4) Next-step suggestions
    next_steps = summary.get("suggested_next_steps") or []
    next_ok = isinstance(next_steps, list) and len(next_steps) >= 1

    # Convenience API: summarize_guided_execution
    summary2 = summarize_guided_execution(plan, steps_executed=step_results)
    conv_ok = (
        (summary2.get("summary_id") or "").startswith("summary-")
        and "key_insights" in summary2
        and "suggested_next_steps" in summary2
    )

    print("copilot insight summarizer OK")
    print("insight extraction: OK" if insight_ok else "insight extraction: FAIL")
    print("signal summary: OK" if signal_ok else "signal summary: FAIL")
    print("risk notes: OK" if risk_ok else "risk notes: FAIL")
    print("next-step suggestions: OK" if (next_ok and conv_ok) else "next-step suggestions: FAIL")

    if not (insight_ok and signal_ok and risk_ok and next_ok and conv_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
