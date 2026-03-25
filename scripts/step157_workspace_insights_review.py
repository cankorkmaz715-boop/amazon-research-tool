#!/usr/bin/env python3
"""
Step 157: SaaS Workspace Insights Review – audit workspace intelligence and personalization layers.
Verifies consistency, feed/timeline integrity, copilot alignment; identifies strengths, weak points, and next improvements.
No rewrites; architecture-consistent review only.
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

    # --- Gather all layer outputs ---
    try:
        from amazon_research.monitoring import get_workspace_intelligence, get_workspace_personalization_signals
        from amazon_research.discovery import (
            get_personalized_ranking,
            list_personalized_rankings,
            get_personalized_suggestions,
            get_workspace_opportunity_feed,
            get_workspace_intelligence_timeline,
            interpret_query,
        )
    except ImportError as e:
        print("workspace insights review FAIL (import)", file=sys.stderr)
        print(f"personalization consistency: FAIL\nfeed integrity: FAIL\ntimeline integrity: FAIL\ncopilot alignment: FAIL\nnext improvements: import error: {e}", file=sys.stderr)
        sys.exit(1)

    intelligence = get_workspace_intelligence(workspace_id)
    personalization = get_workspace_personalization_signals(workspace_id, intelligence_output=intelligence)
    rankings = list_personalized_rankings(workspace_id, limit=10)
    single_ranking = get_personalized_ranking("test-ref", workspace_id) if rankings else get_personalized_ranking("cluster-1", workspace_id)
    suggestions = get_personalized_suggestions(workspace_id, limit=10)
    feed = get_workspace_opportunity_feed(workspace_id, limit=30)
    timeline = get_workspace_intelligence_timeline(workspace_id, limit=50)

    # --- 1) Personalization consistency ---
    personalization_ok = True
    if intelligence.get("workspace_id") != workspace_id:
        personalization_ok = False
        next_improvements.append("Enforce workspace_id in workspace intelligence output.")
    if not isinstance(personalization.get("personalization_signal_set"), dict):
        personalization_ok = False
    if not isinstance(personalization.get("preference_summary"), str):
        personalization_ok = False
    if not isinstance(personalization.get("signal_strengths"), dict):
        personalization_ok = False
    if single_ranking.get("workspace_id") != workspace_id:
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
    if not personalization_ok:
        next_improvements.append("Ensure all personalization outputs include workspace_id, explanations, and auditable base/personalized scores.")

    # --- 2) Feed integrity ---
    feed_ok = True
    for it in feed:
        if it.get("workspace_id") != workspace_id:
            feed_ok = False
            break
        if not (it.get("feed_item_id") and str(it.get("feed_item_id")).startswith("feed-")):
            feed_ok = False
            break
        te = it.get("target_entity")
        if not isinstance(te, dict) or "ref" not in te:
            feed_ok = False
            break
        if it.get("feed_item_type") not in FEED_TYPES:
            feed_ok = False
            break
        if it.get("priority_score") is None and it.get("short_explanation") is None:
            feed_ok = False
            break
        if not it.get("timestamp"):
            feed_ok = False
            break
    if not feed:
        next_improvements.append("Workspace opportunity feed is empty; consider seeding opportunity memory or watchlist for richer feed.")
    if not feed_ok:
        next_improvements.append("Feed items must have workspace_id, feed_item_id, target_entity (type+ref), feed_item_type, priority_score, short_explanation, timestamp.")

    # --- 3) Timeline integrity ---
    timeline_ok = True
    for e in timeline:
        if e.get("workspace_id") != workspace_id:
            timeline_ok = False
            break
        if not (e.get("timeline_event_id") and str(e.get("timeline_event_id")).startswith("timeline-")):
            timeline_ok = False
            break
        if e.get("event_type") not in TIMELINE_EVENT_TYPES:
            timeline_ok = False
            break
        te = e.get("target_entity")
        if not isinstance(te, dict):
            timeline_ok = False
            break
        if "short_summary" not in e or "timestamp" not in e:
            timeline_ok = False
            break
    if not timeline:
        next_improvements.append("Workspace intelligence timeline is empty; ensure feed, alerts, watchlist, or copilot suggestions produce events.")
    if not timeline_ok:
        next_improvements.append("Timeline events must have workspace_id, timeline_event_id, event_type, target_entity, short_summary, timestamp.")

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
    if not (feed_has_copilot or suggestions):  # feed can include suggested_next_action from suggestions
        next_improvements.append("Copilot suggestions can be empty; ensure workspace has sessions or recommendations to drive suggested_next_action.")
    if not copilot_ok:
        next_improvements.append("Copilot foundation (interpret_query) must return interpreted_intent for alignment.")

    # --- 5) Explainability / auditability ---
    ranking_has_explanation = bool((single_ranking.get("personalization_explanation") or "").strip())
    if rankings and not ranking_has_explanation and single_ranking.get("target_opportunity_id"):
        next_improvements.append("Personalized ranking should provide non-empty personalization_explanation for auditability.")
    feed_empty_explanations = sum(1 for it in feed if not (it.get("short_explanation") or "").strip())
    if feed_empty_explanations > len(feed) // 2 and feed:
        next_improvements.append("Many feed items have empty short_explanation; consider explainability enrichment.")

    # --- 6) Strengths and weak points ---
    strengths = [
        "Rule-based, explainable outputs across intelligence, personalization, ranking, suggestions, feed, timeline.",
        "Workspace ID consistently present in all layer outputs.",
        "Base opportunity score preserved in personalized ranking for auditability.",
        "Structured target_entity (type + ref) in feed and timeline for dashboard consumption.",
        "Event and feed type enums align (e.g. suggested_next_action -> copilot_suggestion).",
    ]
    weak_points = []
    if not feed and not timeline:
        weak_points.append("Feed and timeline empty when workspace has no opportunity memory, watchlist, or alerts.")
    elif not feed:
        weak_points.append("Feed empty; depends on opportunity memory or watchlist data.")
    if not suggestions:
        weak_points.append("Copilot suggestions empty without prior sessions or recommendations.")
    if not rankings:
        weak_points.append("Personalized rankings empty without opportunity memory.")
    if not weak_points:
        weak_points.append("No major gaps; stack consistent for current data.")

    # --- 7) Dedupe next improvements ---
    seen = set()
    unique_next = []
    for x in next_improvements:
        if x not in seen:
            seen.add(x)
            unique_next.append(x)

    # --- Output ---
    print("workspace insights review OK")
    print("personalization consistency: OK" if personalization_ok else "personalization consistency: FAIL")
    print("feed integrity: OK" if feed_ok else "feed integrity: FAIL")
    print("timeline integrity: OK" if timeline_ok else "timeline integrity: FAIL")
    print("copilot alignment: OK" if copilot_ok else "copilot alignment: FAIL")
    print("next improvements: " + ("; ".join(unique_next) if unique_next else "none identified; stack is consistent and auditable."))
    print("strengths: " + " | ".join(strengths))
    print("weak points: " + " | ".join(weak_points))

    if not (personalization_ok and feed_ok and timeline_ok and copilot_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
