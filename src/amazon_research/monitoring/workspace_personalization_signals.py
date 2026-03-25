"""
Step 152: Workspace personalization signals – derive workspace-level preference and behavior signals.
Built on workspace intelligence. Produces preferred niches, markets, opportunity patterns,
confidence tolerance, watch/recommendation tendencies. Rule-based, explainable.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.workspace_personalization_signals")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strength_from_count(count: int, total: int) -> str:
    """Map count/total to strength label. Rule-based."""
    if total == 0:
        return "low"
    ratio = count / max(1, total)
    if ratio >= 0.5:
        return "high"
    if ratio >= 0.2:
        return "medium"
    return "low"


def get_workspace_personalization_signals(
    workspace_id: int,
    *,
    intelligence_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Derive workspace-level personalization signals from workspace intelligence (and optional
    recommendation/confidence data). Returns: workspace_id, personalization_signal_set,
    preference_summary, signal_strengths (confidence/strength per inferred preference), timestamp.
    """
    if intelligence_output is None:
        try:
            from amazon_research.monitoring.workspace_intelligence import get_workspace_intelligence
            intelligence_output = get_workspace_intelligence(workspace_id)
        except Exception as e:
            logger.debug("get_workspace_personalization_signals get_workspace_intelligence: %s", e)
            intelligence_output = {}

    focus = intelligence_output.get("focus_areas_summary") or {}
    market = intelligence_output.get("market_activity_summary") or {}
    behavior = intelligence_output.get("research_behavior_summary") or {}
    patterns = intelligence_output.get("notable_patterns_or_tendencies") or []

    # --- Personalization signal set ---
    signal_set: Dict[str, Any] = {}
    signal_strengths: Dict[str, Any] = {}

    # Preferred niche types (from focus areas)
    top_terms = focus.get("top_niche_cluster_terms") or []
    signal_set["preferred_niche_types"] = top_terms[:10]
    signal_strengths["preferred_niche_types"] = "high" if len(top_terms) >= 3 else ("medium" if top_terms else "low")

    # Preferred markets
    markets_mentioned = market.get("markets_mentioned") or []
    mention_counts = market.get("mention_counts") or {}
    signal_set["preferred_markets"] = markets_mentioned
    total_mentions = sum(mention_counts.values()) if isinstance(mention_counts, dict) else 0
    signal_strengths["preferred_markets"] = "high" if total_mentions >= 3 else ("medium" if markets_mentioned else "low")

    # Preferred opportunity pattern (from intent distribution and recommendation usage)
    intent_dist = behavior.get("intent_distribution") or {}
    rec_count = behavior.get("recommendation_count") or 0
    if intent_dist.get("niche_discovery", 0) >= 2 and rec_count >= 2:
        signal_set["preferred_opportunity_pattern"] = "high_opportunity"
    elif intent_dist.get("keyword_exploration", 0) >= 2 or intent_dist.get("trend_exploration", 0) >= 1:
        signal_set["preferred_opportunity_pattern"] = "exploratory"
    else:
        signal_set["preferred_opportunity_pattern"] = "mixed"
    signal_strengths["preferred_opportunity_pattern"] = "medium"

    # Confidence tolerance (infer from strategy/behavior: if we had low-confidence engagement we could set higher tolerance; default medium)
    try:
        from amazon_research.discovery import list_opportunities_with_confidence
        with_conf = list_opportunities_with_confidence(limit=20, workspace_id=workspace_id)
        low_count = sum(1 for c in with_conf if (c.get("confidence_label") or "").lower() == "low")
        if low_count >= 3 and rec_count >= 2:
            signal_set["confidence_tolerance"] = "high"
            signal_strengths["confidence_tolerance"] = "medium"
        elif low_count == 0 and with_conf:
            signal_set["confidence_tolerance"] = "low"
            signal_strengths["confidence_tolerance"] = "medium"
        else:
            signal_set["confidence_tolerance"] = "medium"
            signal_strengths["confidence_tolerance"] = "low"
    except Exception:
        signal_set["confidence_tolerance"] = "medium"
        signal_strengths["confidence_tolerance"] = "low"

    # Watch / recommendation / action tendencies
    watchlist_by_type = focus.get("watchlist_by_type") or {}
    cluster_niche = (watchlist_by_type.get("cluster") or 0) + (watchlist_by_type.get("niche") or 0)
    asin_count = watchlist_by_type.get("asin") or 0
    keyword_count = watchlist_by_type.get("keyword") or 0
    total_watch = cluster_niche + asin_count + keyword_count
    if total_watch == 0:
        signal_set["watch_tendency"] = "none"
    elif cluster_niche >= asin_count and cluster_niche >= keyword_count and cluster_niche > 0:
        signal_set["watch_tendency"] = "cluster_focused"
    elif asin_count >= cluster_niche and asin_count >= keyword_count and asin_count > 0:
        signal_set["watch_tendency"] = "asin_focused"
    elif keyword_count > 0:
        signal_set["watch_tendency"] = "keyword_focused" if keyword_count >= cluster_niche else "mixed"
    else:
        signal_set["watch_tendency"] = "mixed"
    signal_strengths["watch_tendency"] = _strength_from_count(max(cluster_niche, asin_count, keyword_count), max(1, total_watch))

    signal_set["recommendation_usage"] = "active" if rec_count >= 5 else ("moderate" if rec_count >= 1 else "low")
    signal_strengths["recommendation_usage"] = "high" if rec_count >= 5 else ("medium" if rec_count >= 1 else "low")

    # Repeated action tendency (from sessions + threads)
    total_sessions = behavior.get("total_sessions") or 0
    total_threads = behavior.get("total_threads") or 0
    signal_set["repeated_research_tendency"] = "high" if (total_sessions >= 5 or total_threads >= 3) else ("medium" if (total_sessions >= 2 or total_threads >= 1) else "low")
    signal_strengths["repeated_research_tendency"] = signal_set["repeated_research_tendency"]

    # --- Preference summary (human-readable) ---
    parts = []
    if signal_set.get("preferred_niche_types"):
        parts.append(f"Preferred niche/cluster terms: {', '.join(signal_set['preferred_niche_types'][:5])}.")
    if signal_set.get("preferred_markets"):
        parts.append(f"Market preference: {', '.join(signal_set['preferred_markets'])}.")
    parts.append(f"Opportunity pattern: {signal_set.get('preferred_opportunity_pattern', 'mixed')}; confidence tolerance: {signal_set.get('confidence_tolerance', 'medium')}.")
    parts.append(f"Watch tendency: {signal_set.get('watch_tendency', 'none')}; recommendation usage: {signal_set.get('recommendation_usage', 'low')}.")
    preference_summary = " ".join(parts)

    return {
        "workspace_id": workspace_id,
        "personalization_signal_set": signal_set,
        "preference_summary": preference_summary,
        "signal_strengths": signal_strengths,
        "timestamp": _ts(),
    }
