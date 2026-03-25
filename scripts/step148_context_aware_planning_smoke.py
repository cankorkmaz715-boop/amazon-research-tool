#!/usr/bin/env python3
"""Step 148: Context-aware research planning – context usage, follow-up planning, fresh vs follow-up, planning rationale."""
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

    from amazon_research.discovery import (
        get_plan_for_query,
        summarize_guided_execution,
        store_copilot_research_session,
        create_thread,
        build_context_aware_plan,
        get_context_aware_plan_for_query,
    )

    # Seed session + thread for follow-up context
    plan0 = get_plan_for_query("Find niches in kitchen")
    steps0 = plan0.get("ordered_research_steps") or []
    step_results0 = [{"step_order": s.get("step_order"), "step_type": s.get("step_type"), "engines": s.get("suggested_engines") or []} for s in steps0]
    exec0 = {"plan_id": plan0.get("plan_id"), "interpreted_intent": plan0.get("interpreted_intent"), "steps_completed": len(step_results0), "step_results": step_results0}
    summary0 = summarize_guided_execution(plan0, steps_executed=step_results0)
    session_id = store_copilot_research_session(
        copilot_query="Find niches in kitchen",
        plan=plan0,
        execution_output=exec0,
        insight_summary=summary0,
        workspace_id=1,
    )
    create_thread(session_ids=[session_id] if session_id else [], topic="Kitchen niche", anchor="niche:kitchen", workspace_id=1)

    # 1) Context usage: plan has context_references_used with expected keys (use query unlikely to match prior context)
    plan_fresh = build_context_aware_plan("Explore blue widgets xyz unique 123", workspace_id=1)
    context_ok = (
        "context_references_used" in plan_fresh
        and isinstance(plan_fresh["context_references_used"], dict)
        and "matched_thread_id" in plan_fresh["context_references_used"]
        and "matched_session_id" in plan_fresh["context_references_used"]
        and "source_query" in plan_fresh
        and "ordered_research_steps" in plan_fresh
        and "timestamp" in plan_fresh
    )

    # 2) Follow-up planning: query that matches prior context gets is_follow_up and context refs
    plan_followup = build_context_aware_plan("Continue with the same kitchen niche", workspace_id=1)
    followup_ok = (
        plan_followup.get("plan_id") is not None
        and len(plan_followup.get("ordered_research_steps") or []) >= 1
        and (plan_followup.get("is_follow_up") is True or plan_followup.get("context_references_used", {}).get("matched_thread_id") or plan_followup.get("context_references_used", {}).get("matched_session_id"))
    )

    # 3) Fresh vs follow-up: planner distinguishes them (follow-up query gets context match; both plans have is_follow_up and context_references_used)
    ctx_fresh = plan_fresh.get("context_references_used") or {}
    ctx_follow = plan_followup.get("context_references_used") or {}
    has_followup_match = bool(ctx_follow.get("matched_thread_id") or ctx_follow.get("matched_session_id"))
    fresh_ok = "is_follow_up" in plan_fresh and "context_references_used" in plan_fresh
    followup_flag_ok = (plan_followup.get("is_follow_up") is True or has_followup_match) and has_followup_match

    # 4) Planning rationale: non-empty and mentions "follow-up" or "fresh" or "prior"
    rationale_ok = (
        isinstance(plan_fresh.get("planning_rationale"), str)
        and len(plan_fresh.get("planning_rationale") or "") > 0
        and isinstance(plan_followup.get("planning_rationale"), str)
        and len(plan_followup.get("planning_rationale") or "") > 0
    )
    r_fresh = (plan_fresh.get("planning_rationale") or "").lower()
    r_follow = (plan_followup.get("planning_rationale") or "").lower()
    rationale_ok = rationale_ok and ("fresh" in r_fresh or "prior" in r_fresh or "no prior" in r_fresh or "research plan" in r_fresh)
    rationale_ok = rationale_ok and ("follow-up" in r_follow or "continuation" in r_follow or "prior" in r_follow or "matched" in r_follow)

    # Convenience API
    conv_plan = get_context_aware_plan_for_query("Explore keywords", workspace_id=1)
    context_ok = context_ok and "plan_id" in conv_plan and "source_query" in conv_plan

    print("context-aware research planning OK")
    print("context usage: OK" if context_ok else "context usage: FAIL")
    print("follow-up planning: OK" if followup_ok else "follow-up planning: FAIL")
    print("fresh vs follow-up: OK" if (fresh_ok and followup_flag_ok) else "fresh vs follow-up: FAIL")
    print("planning rationale: OK" if rationale_ok else "planning rationale: FAIL")

    if not (context_ok and followup_ok and fresh_ok and followup_flag_ok and rationale_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
