#!/usr/bin/env python3
"""Step 147: Follow-up research resolver – thread matching, session matching, follow-up classification, copilot compatibility."""
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
        add_session_to_thread,
        resolve_followup,
        resolve_followup_to_session_or_thread,
        interpret_query,
        FOLLOWUP_SAME_NICHE,
        FOLLOWUP_SAME_ASIN_PRODUCT_CLUSTER,
        FOLLOWUP_SIMILAR_RELATED_COMPARE,
        FOLLOWUP_NONE,
    )

    # Seed: one session + one thread (kitchen niche)
    plan = get_plan_for_query("Find niches in kitchen")
    steps = plan.get("ordered_research_steps") or []
    step_results = [{"step_order": s.get("step_order"), "step_type": s.get("step_type"), "engines": s.get("suggested_engines") or []} for s in steps]
    execution_output = {"plan_id": plan.get("plan_id"), "interpreted_intent": plan.get("interpreted_intent"), "steps_completed": len(step_results), "step_results": step_results}
    summary = summarize_guided_execution(plan, steps_executed=step_results)
    session_id_1 = store_copilot_research_session(
        copilot_query="Find niches in kitchen",
        plan=plan,
        execution_output=execution_output,
        insight_summary=summary,
        workspace_id=1,
    )
    thread_id = create_thread(session_ids=[session_id_1] if session_id_1 else [], topic="Kitchen niche follow-up", anchor="niche:kitchen", workspace_id=1)

    # 1) Thread matching: follow-up query that matches thread topic
    r1 = resolve_followup("Continue with the same kitchen niche", workspace_id=1)
    thread_matching_ok = (
        r1.get("resolver_result_id") is not None
        and (r1.get("matched_thread_id") is not None or r1.get("matched_session_id") is not None)
        and "follow_up_type" in r1
        and "timestamp" in r1
    )
    if thread_id and r1.get("matched_thread_id"):
        thread_matching_ok = thread_matching_ok and r1.get("matched_thread_id") == thread_id

    # 2) Session matching: query similar to prior session
    r2 = resolve_followup("Find niches in kitchen", workspace_id=1)
    session_matching_ok = (
        r2.get("resolver_result_id") is not None
        and (r2.get("matched_thread_id") or r2.get("matched_session_id"))
        and ("match_rationale" in r2 or "confidence" in r2)
    )

    # 3) Follow-up classification
    r3 = resolve_followup("Similar products in that cluster", workspace_id=1)
    valid_types = (FOLLOWUP_SAME_NICHE, FOLLOWUP_SAME_ASIN_PRODUCT_CLUSTER, FOLLOWUP_SIMILAR_RELATED_COMPARE, FOLLOWUP_NONE, "market_specific_followup")
    classification_ok = r3.get("follow_up_type") in valid_types
    r4 = resolve_followup("Compare with same niche", workspace_id=1)
    classification_ok = classification_ok and r4.get("follow_up_type") in valid_types

    # 4) Copilot compatibility: interpret_query used inside resolver; output structure
    interp = interpret_query("Continue that research")
    copilot_ok = interp.get("interpreted_intent") is not None and "research_plan_summary" in interp or "interpreted_intent" in interp
    out = resolve_followup("Random new topic xyz abc", workspace_id=1)
    copilot_ok = (
        copilot_ok
        and out.get("resolver_result_id") is not None
        and "matched_thread_id" in out
        and "matched_session_id" in out
        and "follow_up_type" in out
        and "timestamp" in out
    )
    single = resolve_followup_to_session_or_thread("Continue kitchen", workspace_id=1)
    copilot_ok = copilot_ok and (single is None or (single.get("matched_thread_id") or single.get("matched_session_id")))

    print("follow-up research resolver OK")
    print("thread matching: OK" if thread_matching_ok else "thread matching: FAIL")
    print("session matching: OK" if session_matching_ok else "session matching: FAIL")
    print("follow-up classification: OK" if classification_ok else "follow-up classification: FAIL")
    print("copilot compatibility: OK" if copilot_ok else "copilot compatibility: FAIL")

    if not (thread_matching_ok and session_matching_ok and classification_ok and copilot_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
