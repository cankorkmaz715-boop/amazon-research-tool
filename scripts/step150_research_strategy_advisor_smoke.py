#!/usr/bin/env python3
"""Step 150: Copilot research strategy advisor – strategy analysis, direction suggestions, risk analysis, copilot compatibility."""
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
        get_research_strategy,
        get_strategy_for_comparison,
        run_comparative_research,
        interpret_query,
    )

    # 1) Strategy analysis: required structure and analyzed context
    strategy = get_research_strategy(workspace_id=1)
    analysis_ok = (
        (strategy.get("strategy_id") or "").startswith("strategy-")
        and "analyzed_research_context" in strategy
        and isinstance(strategy["analyzed_research_context"], dict)
        and "opportunity_count" in strategy["analyzed_research_context"]
        and "timestamp" in strategy
    )

    # 2) Direction suggestions: recommended_research_directions list with direction_type, target, rationale
    directions = strategy.get("recommended_research_directions") or []
    direction_ok = isinstance(directions, list)
    if directions:
        direction_ok = direction_ok and all(
            "direction_type" in d and "rationale" in d for d in directions[:3]
        )

    # 3) Risk analysis: risk_notes list and reasoning_summary
    risk_ok = "risk_notes" in strategy and isinstance(strategy.get("risk_notes"), list)
    risk_ok = risk_ok and "reasoning_summary" in strategy and len(strategy.get("reasoning_summary") or "") > 0

    # 4) Copilot compatibility: strategy from comparison output; interpret_query works
    comparison = run_comparative_research(
        [{"type": "niche", "label": "kitchen"}, {"type": "niche", "label": "garden"}],
        workspace_id=1,
    )
    strategy2 = get_strategy_for_comparison(comparison, workspace_id=1)
    copilot_ok = (
        strategy2.get("strategy_id") is not None
        and (strategy2.get("analyzed_research_context") or {}).get("comparison_summary") is not None
    )
    interp = interpret_query("Find niches in kitchen")
    copilot_ok = copilot_ok and interp.get("interpreted_intent") is not None

    print("copilot research strategy advisor OK")
    print("strategy analysis: OK" if analysis_ok else "strategy analysis: FAIL")
    print("direction suggestions: OK" if direction_ok else "direction suggestions: FAIL")
    print("risk analysis: OK" if risk_ok else "risk analysis: FAIL")
    print("copilot compatibility: OK" if copilot_ok else "copilot compatibility: FAIL")

    if not (analysis_ok and direction_ok and risk_ok and copilot_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
