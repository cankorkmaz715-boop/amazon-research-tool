#!/usr/bin/env python3
"""Step 158: Workspace recommendation loops – recommendation tracking, action linkage, loop reinforcement, workspace compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import (
        record_recommendation_loop,
        list_recommendation_loops,
        get_loop_reinforcement_signals,
        get_loop_reinforcement_for_personalization,
        ACTION_FOLLOW_UP_RESEARCH,
        ACTION_WATCHLIST_ADDITION,
        ACTION_COPILOT_QUERY,
        ACTION_DEEPER_ANALYSIS,
        REINFORCEMENT_POSITIVE,
        REINFORCEMENT_NEUTRAL,
    )

    workspace_id = 1

    # 1) Recommendation tracking: record loops with required fields
    r1 = record_recommendation_loop(
        workspace_id,
        "reco-001",
        ACTION_FOLLOW_UP_RESEARCH,
        loop_reinforcement_signal=REINFORCEMENT_POSITIVE,
        target_entity_ref="cluster-kitchen",
    )
    r2 = record_recommendation_loop(
        workspace_id,
        "feed-abc123",
        ACTION_WATCHLIST_ADDITION,
        loop_reinforcement_signal=REINFORCEMENT_POSITIVE,
        target_entity_ref="niche-gadgets",
    )
    r3 = record_recommendation_loop(
        workspace_id,
        "suggest-xyz",
        ACTION_COPILOT_QUERY,
        loop_reinforcement_signal=REINFORCEMENT_NEUTRAL,
    )
    tracking_ok = all(
        r.get("workspace_id") == workspace_id
        and r.get("recommendation_id")
        and r.get("resulting_user_action_type")
        and r.get("loop_reinforcement_signal")
        and r.get("timestamp")
        for r in (r1, r2, r3)
    )

    # 2) Action linkage: list returns records linked to workspace and recommendation ids
    listed = list_recommendation_loops(workspace_id, limit=10)
    action_linkage_ok = len(listed) >= 3 and all(
        item.get("workspace_id") == workspace_id and item.get("recommendation_id") for item in listed
    )
    rec_ids = {item.get("recommendation_id") for item in listed}
    action_linkage_ok = action_linkage_ok and ("reco-001" in rec_ids or "feed-abc123" in rec_ids)

    # 3) Loop reinforcement: get_loop_reinforcement_signals returns aggregation for personalization
    signals = get_loop_reinforcement_signals(workspace_id, limit=50)
    reinforcement_ok = (
        signals.get("workspace_id") == workspace_id
        and "reinforcement_by_action_type" in signals
        and "reinforced_entity_refs" in signals
        and "total_loops" in signals
        and isinstance(signals["reinforced_entity_refs"], list)
    )
    personalization_input = get_loop_reinforcement_for_personalization(workspace_id)
    reinforcement_ok = reinforcement_ok and "reinforced_entity_refs" in personalization_input and "total_loops" in personalization_input

    # 4) Workspace compatibility: works with workspace intelligence / feed / suggestions (same workspace_id)
    from amazon_research.monitoring import get_workspace_intelligence
    from amazon_research.discovery import get_workspace_opportunity_feed, get_personalized_suggestions
    intelligence = get_workspace_intelligence(workspace_id)
    feed = get_workspace_opportunity_feed(workspace_id, limit=5)
    suggestions = get_personalized_suggestions(workspace_id, limit=5)
    workspace_ok = intelligence.get("workspace_id") == workspace_id
    workspace_ok = workspace_ok and all(it.get("workspace_id") == workspace_id for it in feed)
    workspace_ok = workspace_ok and all(s.get("workspace_id") == workspace_id for s in suggestions)
    workspace_ok = workspace_ok and listed and listed[0].get("workspace_id") == workspace_id

    print("workspace recommendation loops OK")
    print("recommendation tracking: OK" if tracking_ok else "recommendation tracking: FAIL")
    print("action linkage: OK" if action_linkage_ok else "action linkage: FAIL")
    print("loop reinforcement: OK" if reinforcement_ok else "loop reinforcement: FAIL")
    print("workspace compatibility: OK" if workspace_ok else "workspace compatibility: FAIL")

    if not (tracking_ok and action_linkage_ok and reinforcement_ok and workspace_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
