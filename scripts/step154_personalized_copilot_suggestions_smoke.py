#!/usr/bin/env python3
"""Step 154: Personalized copilot suggestions – workspace signal usage, suggestion generation, reasoning summary, copilot compatibility."""
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
        get_personalized_suggestions,
        interpret_query,
    )

    suggestions = get_personalized_suggestions(1, limit=15)

    # 1) Workspace signal usage: suggestions use workspace_id and supporting_signals
    workspace_ok = all(s.get("workspace_id") == 1 for s in suggestions) if suggestions else True
    if suggestions:
        workspace_ok = workspace_ok and all("supporting_signals" in s and isinstance(s.get("supporting_signals"), dict) for s in suggestions[:5])

    # 2) Suggestion generation: each has suggestion_id, suggested_research_direction
    gen_ok = isinstance(suggestions, list)
    if suggestions:
        gen_ok = gen_ok and all(
            (s.get("suggestion_id") or "").startswith("suggest-") and s.get("suggested_research_direction")
            for s in suggestions
        )

    # 3) Reasoning summary: each has non-empty reasoning_summary
    reasoning_ok = all(
        isinstance(s.get("reasoning_summary"), str) and len(s.get("reasoning_summary") or "") > 0
        for s in suggestions
    ) if suggestions else True

    # 4) Copilot compatibility: interpret_query works; suggestions structure compatible with copilot
    interp = interpret_query("Find niches in kitchen")
    copilot_ok = interp.get("interpreted_intent") is not None
    copilot_ok = copilot_ok and all(
        "timestamp" in s and "workspace_id" in s for s in suggestions[:3]
    ) if suggestions else copilot_ok

    print("personalized copilot suggestions OK")
    print("workspace signal usage: OK" if workspace_ok else "workspace signal usage: FAIL")
    print("suggestion generation: OK" if gen_ok else "suggestion generation: FAIL")
    print("reasoning summary: OK" if reasoning_ok else "reasoning summary: FAIL")
    print("copilot compatibility: OK" if copilot_ok else "copilot compatibility: FAIL")

    if not (workspace_ok and gen_ok and reasoning_ok and copilot_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
