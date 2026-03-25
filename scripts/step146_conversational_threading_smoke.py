#!/usr/bin/env python3
"""Step 146: Conversational research threading – thread creation, session linking, thread summary, history."""
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
        get_copilot_research_session,
        create_thread,
        get_thread,
        add_session_to_thread,
        list_threads,
        get_thread_summary,
    )

    # Build two sessions to link into a thread
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
    session_id_2 = store_copilot_research_session(
        copilot_query="Explore keywords for supplements",
        interpreted_intent="keyword_exploration",
        research_plan_ref="plan-other",
        workspace_id=1,
    )

    # 1) Thread creation
    thread_id = create_thread(
        session_ids=[session_id_1] if session_id_1 else [],
        topic="Kitchen niche follow-up",
        anchor="niche:kitchen",
        workspace_id=1,
    )
    thread_creation_ok = thread_id is not None and isinstance(thread_id, str) and thread_id.startswith("thread-")

    # 2) Session linking (add second session to thread)
    if thread_id and session_id_2:
        linked = add_session_to_thread(thread_id, session_id_2, workspace_id=1)
        session_linking_ok = linked
    else:
        session_linking_ok = thread_id is not None
    if thread_id:
        t = get_thread(thread_id, workspace_id=1)
        session_linking_ok = session_linking_ok and t is not None and len(t.get("linked_session_ids") or []) >= 1

    # 3) Thread summary
    summ = get_thread_summary(thread_id, workspace_id=1) if thread_id else None
    summary_ok = (
        summ is not None
        and summ.get("thread_id") == thread_id
        and "linked_session_ids" in summ
        and "thread_summary" in summ
        and (summ.get("thread_summary") or summ.get("thread_topic"))
        and "latest_session_reference" in summ
    )

    # 4) History compatibility
    threads = list_threads(workspace_id=1, limit=10)
    history_ok = isinstance(threads, list) and (len(threads) >= 1 if thread_id else True)
    if thread_id and threads:
        found = any(t.get("thread_id") == thread_id for t in threads)
        history_ok = history_ok and found

    print("conversational research threading OK")
    print("thread creation: OK" if thread_creation_ok else "thread creation: FAIL")
    print("session linking: OK" if session_linking_ok else "session linking: FAIL")
    print("thread summary: OK" if summary_ok else "thread summary: FAIL")
    print("history compatibility: OK" if history_ok else "history compatibility: FAIL")

    if not (thread_creation_ok and session_linking_ok and summary_ok and history_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
