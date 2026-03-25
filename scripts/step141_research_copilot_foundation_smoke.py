#!/usr/bin/env python3
"""Step 141: Research copilot layer (foundation) – query interpretation, intent extraction, research plan, engine routing."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

INTENTS = ("niche_discovery", "product_opportunity_search", "keyword_exploration", "trend_exploration")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import interpret_query, plan_to_action_hints

    # Query interpretation: required output shape
    out = interpret_query("Find niches in kitchen products")
    query_ok = (
        "copilot_request_id" in out
        and (out.get("copilot_request_id") or "").startswith("copilot-")
        and "interpreted_intent" in out
        and "research_plan_summary" in out
        and "engines_suggested" in out
        and "timestamp" in out
    )

    # Intent extraction: niche discovery
    niche_out = interpret_query("I want to discover new niches")
    intent_ok = niche_out.get("interpreted_intent") == "niche_discovery"
    # Product opportunity
    opp_out = interpret_query("Show me product opportunities")
    intent_ok = intent_ok and opp_out.get("interpreted_intent") == "product_opportunity_search"
    # Keyword exploration
    kw_out = interpret_query("Explore keywords for supplements")
    intent_ok = intent_ok and kw_out.get("interpreted_intent") == "keyword_exploration"
    # Trend exploration
    trend_out = interpret_query("What are the trends in electronics?")
    intent_ok = intent_ok and trend_out.get("interpreted_intent") == "trend_exploration"

    # Research plan generation: summary has intent, entity_type, engines_suggested
    plan = out.get("research_plan_summary") or {}
    plan_ok = (
        "intent" in plan
        and plan.get("intent") in INTENTS
        and "entity_type" in plan
        and "engines_suggested" in plan
        and isinstance(plan.get("engines_suggested"), list)
    )

    # Engine routing: engines_suggested list matches intent
    engines = out.get("engines_suggested") or []
    engine_ok = isinstance(engines, list) and len(engines) >= 1
    hints = plan_to_action_hints(out)
    engine_ok = engine_ok and isinstance(hints, list) and (len(hints) == 0 or "engine" in hints[0])

    print("research copilot layer OK")
    print("query interpretation: OK" if query_ok else "query interpretation: FAIL")
    print("intent extraction: OK" if intent_ok else "intent extraction: FAIL")
    print("research plan generation: OK" if plan_ok else "research plan generation: FAIL")
    print("engine routing: OK" if engine_ok else "engine routing: FAIL")

    if not (query_ok and intent_ok and plan_ok and engine_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
