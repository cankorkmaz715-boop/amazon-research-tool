#!/usr/bin/env python3
"""Step 145: Copilot research memory – session record, plan linkage, summary linkage, history compatibility."""
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
        pass  # Use in-memory fallback when DB is unavailable

    from amazon_research.discovery import (
        get_plan_for_query,
        build_insight_summary,
        summarize_guided_execution,
        store_copilot_research_session,
        get_copilot_research_session,
        list_copilot_research_sessions,
        link_copilot_research_sessions,
    )

    # Build plan and summary as in guided execution flow
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
    summary = summarize_guided_execution(plan, steps_executed=step_results)

    # 1) Session record: store and retrieve with required fields
    session_id = store_copilot_research_session(
        copilot_query="Find niches in kitchen",
        plan=plan,
        execution_output=execution_output,
        insight_summary=summary,
        workspace_id=1,
    )
    session_ok = session_id is not None and isinstance(session_id, str) and len(session_id) > 0

    rec = get_copilot_research_session(session_id, workspace_id=1) if session_id else None
    session_ok = session_ok and rec is not None
    if rec:
        session_ok = (
            session_ok
            and rec.get("session_id") == session_id
            and "copilot_query" in rec
            and "interpreted_intent" in rec
            and "created_at" in rec
            and "updated_at" in rec
        )

    # 2) Plan linkage
    plan_ref = rec.get("research_plan_ref") if rec else None
    plan_link_ok = plan_ref is not None and plan_ref == plan.get("plan_id")

    # 3) Summary linkage
    summary_ref = rec.get("insight_summary_ref") if rec else None
    summary_link_ok = summary_ref is not None and summary_ref == summary.get("summary_id")

    # 4) History compatibility: list and link
    sessions = list_copilot_research_sessions(workspace_id=1, limit=10)
    history_ok = isinstance(sessions, list) and (len(sessions) >= 1 if session_id else True)
    if session_id and sessions:
        found = any(s.get("session_id") == session_id for s in sessions)
        history_ok = history_ok and found

    # Link a second session to the first
    session_id_2 = store_copilot_research_session(
        copilot_query="Explore keywords for supplements",
        interpreted_intent="keyword_exploration",
        research_plan_ref="plan-other",
        workspace_id=1,
    )
    if session_id and session_id_2:
        linked = link_copilot_research_sessions(session_id, session_id_2, workspace_id=1)
        rec_after = get_copilot_research_session(session_id, workspace_id=1)
        history_ok = history_ok and linked and rec_after is not None and session_id_2 in (rec_after.get("related_session_ids") or [])

    print("copilot research memory OK")
    print("session record: OK" if session_ok else "session record: FAIL")
    print("plan linkage: OK" if plan_link_ok else "plan linkage: FAIL")
    print("summary linkage: OK" if summary_link_ok else "summary linkage: FAIL")
    print("history compatibility: OK" if history_ok else "history compatibility: FAIL")

    if not (session_ok and plan_link_ok and summary_link_ok and history_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
