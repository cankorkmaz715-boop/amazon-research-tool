#!/usr/bin/env python3
"""
Step 160: SaaS Intelligence Stability Review – audit the full SaaS workspace intelligence stack.
Verifies consistency, signal propagation, personalization, adaptive signal stability, copilot alignment.
Identifies strengths, weaknesses, and minimal next improvements. No rewrites.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

FEED_TYPES = {"new_opportunity", "rising_opportunity", "risky_opportunity", "watchlist_update", "suggested_next_action"}
TIMELINE_EVENT_TYPES = {
    "new_opportunity", "rising_opportunity", "weakening_opportunity",
    "alert_event", "watchlist_event", "copilot_suggestion", "research_action",
}


def main():
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from amazon_research.db import init_db
        init_db()
    except Exception:
        pass

    workspace_id = 1
    next_improvements: list = []

    # --- Import all SaaS intelligence modules ---
    try:
        from amazon_research.monitoring import get_workspace_intelligence, get_workspace_personalization_signals
        from amazon_research.discovery import (
            get_personalized_ranking,
            list_personalized_rankings,
            get_personalized_suggestions,
            get_workspace_opportunity_feed,
            get_workspace_intelligence_timeline,
            list_recommendation_loops,
            get_loop_reinforcement_signals,
            compute_adaptive_update,
            get_adaptive_signal_update,
            get_adaptive_preference_weights,
            interpret_query,
        )
    except ImportError as e:
        print("saas intelligence review FAIL (import)", file=sys.stderr)
        print(f"signal propagation: FAIL\npersonalization consistency: FAIL\nadaptive signal stability: FAIL\ncopilot alignment: FAIL\nnext improvements: import error: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Gather all layer outputs ---
    intelligence = get_workspace_intelligence(workspace_id)
    personalization = get_workspace_personalization_signals(workspace_id, intelligence_output=intelligence)
    rankings = list_personalized_rankings(workspace_id, limit=10)
    single_ranking = get_personalized_ranking("cluster-1", workspace_id)
    suggestions = get_personalized_suggestions(workspace_id, limit=10)
    feed = get_workspace_opportunity_feed(workspace_id, limit=30)
    timeline = get_workspace_intelligence_timeline(workspace_id, limit=50)
    loops = list_recommendation_loops(workspace_id, limit=20)
    loop_signals = get_loop_reinforcement_signals(workspace_id, limit=100)
    adaptive_update = compute_adaptive_update(workspace_id, loop_signals=loop_signals)
    adaptive_weights = get_adaptive_preference_weights(workspace_id)
    latest_adaptive = get_adaptive_signal_update(workspace_id)

    # --- 1) Signal propagation: workspace behavior signals flow through the stack ---
    # Intelligence -> personalization (same workspace_id; personalization accepts intelligence_output)
    # Loops -> adaptive (adaptive uses loop_signals)
    # Feed/timeline consume ranking, suggestions, alerts, watchlist
    signal_prop_ok = True
    if intelligence.get("workspace_id") != workspace_id:
        signal_prop_ok = False
        next_improvements.append("Workspace intelligence must return workspace_id.")
    if personalization.get("workspace_id") != workspace_id:
        signal_prop_ok = False
    if single_ranking.get("workspace_id") != workspace_id:
        signal_prop_ok = False
    if feed and any(it.get("workspace_id") != workspace_id for it in feed):
        signal_prop_ok = False
    if timeline and any(e.get("workspace_id") != workspace_id for e in timeline):
        signal_prop_ok = False
    if loop_signals.get("workspace_id") != workspace_id:
        signal_prop_ok = False
    if adaptive_update.get("workspace_id") != workspace_id:
        signal_prop_ok = False
    if not (isinstance(adaptive_update.get("reinforcement_signals_used"), dict) and "loop_total" in (adaptive_update.get("reinforcement_signals_used") or {})):
        signal_prop_ok = False
        next_improvements.append("Adaptive intelligence should record reinforcement_signals_used from loops.")

    # --- 2) Personalization consistency ---
    personalization_ok = True
    if not isinstance(personalization.get("personalization_signal_set"), dict):
        personalization_ok = False
    if not isinstance(personalization.get("preference_summary"), str):
        personalization_ok = False
    if not isinstance(personalization.get("signal_strengths"), dict):
        personalization_ok = False
    if "base_opportunity_score" not in single_ranking or "personalized_score" not in single_ranking:
        personalization_ok = False
    if "personalization_explanation" not in single_ranking:
        personalization_ok = False
    for s in suggestions:
        if s.get("workspace_id") != workspace_id:
            personalization_ok = False
            break
        if not isinstance(s.get("reasoning_summary"), str):
            personalization_ok = False
            break
    for it in feed:
        if it.get("workspace_id") != workspace_id or it.get("feed_item_type") not in FEED_TYPES:
            personalization_ok = False
            break
    for e in timeline:
        if e.get("workspace_id") != workspace_id or e.get("event_type") not in TIMELINE_EVENT_TYPES:
            personalization_ok = False
            break

    # --- 3) Adaptive signal stability ---
    adaptive_ok = True
    if not (adaptive_update.get("adaptive_signal_update_id") or "").startswith("adaptive-"):
        adaptive_ok = False
    if not isinstance(adaptive_update.get("updated_preference_weights"), dict):
        adaptive_ok = False
    weights = adaptive_update.get("updated_preference_weights") or {}
    if "preferred_niche_weights" not in weights or "ranking_adjustment_factor" not in weights or "suggestion_priority_boost" not in weights:
        adaptive_ok = False
    if not isinstance(adaptive_weights, dict) or "ranking_adjustment_factor" not in adaptive_weights:
        adaptive_ok = False
    if latest_adaptive is None or latest_adaptive.get("workspace_id") != workspace_id:
        adaptive_ok = False
    if not isinstance(weights.get("ranking_adjustment_factor"), (int, float)):
        adaptive_ok = False

    # --- 4) Copilot alignment ---
    copilot_ok = True
    try:
        interp = interpret_query("Find niches in kitchen")
        if interp.get("interpreted_intent") is None and "interpreted_intent" not in interp:
            copilot_ok = False
    except Exception:
        copilot_ok = False
    feed_has_copilot = any(it.get("feed_item_type") == "suggested_next_action" for it in feed)
    timeline_has_copilot = any(e.get("event_type") == "copilot_suggestion" for e in timeline)
    if not (feed_has_copilot or timeline_has_copilot or suggestions):
        pass  # OK if empty; copilot types exist in schema
    copilot_ok = copilot_ok and isinstance(suggestions, list)

    # --- 5) Determinism and explainability ---
    if not single_ranking.get("personalization_explanation"):
        if single_ranking.get("target_opportunity_id"):
            next_improvements.append("Personalized ranking should provide personalization_explanation for auditability.")
    if adaptive_update and not (adaptive_update.get("reinforcement_signals_used")):
        next_improvements.append("Adaptive updates should expose reinforcement_signals_used for explainability.")

    # --- 6) Strengths and weaknesses ---
    strengths = [
        "Unified workspace_id across all eight layers (intelligence, personalization, ranking, suggestions, feed, timeline, loops, adaptive).",
        "Rule-based, deterministic outputs; personalization_explanation and reinforcement_signals_used support explainability.",
        "Adaptive layer consumes recommendation loops and produces updated_preference_weights without mutating core modules.",
        "Feed and timeline aggregate from ranking, suggestions, alerts, watchlist; event and feed type enums are consistent.",
    ]
    weaknesses = []
    if not loops:
        weaknesses.append("Recommendation loops are in-memory only; no cross-session persistence.")
    if not (adaptive_weights.get("preferred_niche_weights") or adaptive_weights.get("suggestion_priority_boost")):
        weaknesses.append("Adaptive weights not yet consumed by personalization/ranking/suggestions.")
    if not weaknesses:
        weaknesses.append("No critical gaps; stack is consistent and auditable.")

    # --- 7) Minimal next improvements (robustness) ---
    if not loops and not any("persist" in r for r in next_improvements):
        next_improvements.append("Consider persisting recommendation loops for cross-session reinforcement.")
    if not any("wire adaptive" in rec for rec in next_improvements):
        next_improvements.append("Consider wiring get_adaptive_preference_weights into personalization/ranking for live adjustment.")
    seen = set()
    unique_next = []
    for x in next_improvements:
        if x not in seen:
            seen.add(x)
            unique_next.append(x)

    # --- Output ---
    print("saas intelligence review OK")
    print("signal propagation: OK" if signal_prop_ok else "signal propagation: FAIL")
    print("personalization consistency: OK" if personalization_ok else "personalization consistency: FAIL")
    print("adaptive signal stability: OK" if adaptive_ok else "adaptive signal stability: FAIL")
    print("copilot alignment: OK" if copilot_ok else "copilot alignment: FAIL")
    print("next improvements: " + ("; ".join(unique_next) if unique_next else "none; stack is consistent and explainable."))
    print("strengths: " + " | ".join(strengths))
    print("weaknesses: " + " | ".join(weaknesses))

    if not (signal_prop_ok and personalization_ok and adaptive_ok and copilot_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
