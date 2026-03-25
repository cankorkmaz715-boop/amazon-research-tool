#!/usr/bin/env python3
"""Step 159: Workspace adaptive intelligence – signal reinforcement, preference update, ranking/suggestion compatibility."""
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
        compute_adaptive_update,
        get_adaptive_signal_update,
        get_adaptive_preference_weights,
        get_personalized_ranking,
        get_personalized_suggestions,
        ACTION_FOLLOW_UP_RESEARCH,
        REINFORCEMENT_POSITIVE,
    )

    workspace_id = 1

    # Seed a loop so adaptive update has reinforcement data
    record_recommendation_loop(
        workspace_id,
        "reco-adapt-1",
        ACTION_FOLLOW_UP_RESEARCH,
        loop_reinforcement_signal=REINFORCEMENT_POSITIVE,
        target_entity_ref="cluster-kitchen",
    )

    # 1) Signal reinforcement: compute_adaptive_update uses loop signals
    update = compute_adaptive_update(workspace_id)
    reinforcement_ok = (
        update.get("workspace_id") == workspace_id
        and (update.get("adaptive_signal_update_id") or "").startswith("adaptive-")
        and "reinforcement_signals_used" in update
        and isinstance(update["reinforcement_signals_used"], dict)
    )
    used = update.get("reinforcement_signals_used") or {}
    reinforcement_ok = reinforcement_ok and "loop_total" in used and "reinforced_entity_refs_count" in used

    # 2) Preference update: updated_preference_weights present and structured
    weights = update.get("updated_preference_weights") or {}
    preference_ok = (
        "preferred_niche_weights" in weights
        and "ranking_adjustment_factor" in weights
        and "suggestion_priority_boost" in weights
        and isinstance(weights["preferred_niche_weights"], dict)
        and isinstance(weights["suggestion_priority_boost"], dict)
    )

    # 3) Ranking adjustment compatibility: get_adaptive_preference_weights returns weights ranking can use
    adaptive_weights = get_adaptive_preference_weights(workspace_id)
    ranking_ok = (
        "ranking_adjustment_factor" in adaptive_weights
        and "preferred_niche_weights" in adaptive_weights
        and isinstance(adaptive_weights.get("ranking_adjustment_factor"), (int, float))
    )
    # Personalized ranking still works and can consume adaptive weights (structure compatible)
    rank_out = get_personalized_ranking("cluster-kitchen", workspace_id)
    ranking_ok = ranking_ok and rank_out.get("workspace_id") == workspace_id and "personalized_score" in rank_out

    # 4) Copilot compatibility: get_adaptive_signal_update and suggestions work together
    latest = get_adaptive_signal_update(workspace_id)
    suggestions = get_personalized_suggestions(workspace_id, limit=5)
    copilot_ok = latest is not None and latest.get("workspace_id") == workspace_id
    copilot_ok = copilot_ok and "updated_preference_weights" in latest
    copilot_ok = copilot_ok and isinstance(suggestions, list) and all(s.get("workspace_id") == workspace_id for s in suggestions)

    print("workspace adaptive intelligence OK")
    print("signal reinforcement: OK" if reinforcement_ok else "signal reinforcement: FAIL")
    print("preference update: OK" if preference_ok else "preference update: FAIL")
    print("ranking adjustment compatibility: OK" if ranking_ok else "ranking adjustment compatibility: FAIL")
    print("copilot compatibility: OK" if copilot_ok else "copilot compatibility: FAIL")

    if not (reinforcement_ok and preference_ok and ranking_ok and copilot_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
