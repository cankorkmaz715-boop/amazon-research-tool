"""
Step 154: Personalized copilot suggestions – personalization-aware suggestion layer for the research copilot.
Uses workspace focus areas, personalization signals, personalized opportunity ranking, prior sessions,
prior recommendations. Suggests niches, clusters, markets, follow-up directions. Rule-based, explainable.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.personalized_copilot_suggestions")

# Suggestion direction types
SUGGESTION_NICHE_EXPLORE = "niche_to_explore"
SUGGESTION_CLUSTER_DEEPER = "cluster_deeper_analysis"
SUGGESTION_MARKET_ALIGNED = "market_aligned"
SUGGESTION_FOLLOW_UP = "follow_up_direction"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_personalized_suggestions(
    workspace_id: int,
    *,
    limit: int = 20,
    intelligence_output: Optional[Dict[str, Any]] = None,
    personalization_output: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate personalized copilot suggestions from workspace intelligence, personalization signals,
    personalized opportunity ranking, and prior sessions/recommendations. Returns list of
    { workspace_id, suggestion_id, suggested_research_direction, supporting_signals, reasoning_summary, timestamp }.
    """
    suggestions: List[Dict[str, Any]] = []

    # 1) Workspace intelligence
    if intelligence_output is None:
        try:
            from amazon_research.monitoring import get_workspace_intelligence
            intelligence_output = get_workspace_intelligence(workspace_id)
        except Exception as e:
            logger.debug("get_personalized_suggestions get_workspace_intelligence: %s", e)
            intelligence_output = {}
    focus = intelligence_output.get("focus_areas_summary") or {}
    market = intelligence_output.get("market_activity_summary") or {}
    behavior = intelligence_output.get("research_behavior_summary") or {}

    # 2) Personalization signals
    if personalization_output is None:
        try:
            from amazon_research.monitoring import get_workspace_personalization_signals
            personalization_output = get_workspace_personalization_signals(workspace_id, intelligence_output=intelligence_output)
        except Exception as e:
            logger.debug("get_personalized_suggestions get_workspace_personalization_signals: %s", e)
            personalization_output = {}
    signal_set = (personalization_output.get("personalization_signal_set") or {}) if isinstance(personalization_output, dict) else {}

    # 3) Niches worth exploring (from focus areas / preferred niche types)
    top_terms = focus.get("top_niche_cluster_terms") or signal_set.get("preferred_niche_types") or []
    for term in (top_terms[:5] if top_terms else []):
        suggestions.append({
            "workspace_id": workspace_id,
            "suggestion_id": f"suggest-{uuid.uuid4().hex[:10]}",
            "suggested_research_direction": f"Explore niche: {term}",
            "direction_type": SUGGESTION_NICHE_EXPLORE,
            "supporting_signals": {"source": "workspace_focus", "term": term},
            "reasoning_summary": f"Niche '{term}' appears in workspace focus; worth exploring further.",
            "timestamp": _ts(),
        })

    # 4) Clusters worth deeper analysis (from personalized opportunity ranking)
    try:
        from amazon_research.discovery import list_personalized_rankings
        ranked = list_personalized_rankings(workspace_id, limit=5)
        for r in ranked[:3]:
            ref = r.get("target_opportunity_id")
            if not ref:
                continue
            score = r.get("personalized_score") or 0
            suggestions.append({
                "workspace_id": workspace_id,
                "suggestion_id": f"suggest-{uuid.uuid4().hex[:10]}",
                "suggested_research_direction": f"Deeper analysis: cluster {ref}",
                "direction_type": SUGGESTION_CLUSTER_DEEPER,
                "supporting_signals": {"source": "personalized_ranking", "opportunity_id": ref, "personalized_score": score},
                "reasoning_summary": f"Cluster {ref} ranks highly ({score}) for this workspace; consider deeper analysis.",
                "timestamp": _ts(),
            })
    except Exception as e:
        logger.debug("get_personalized_suggestions list_personalized_rankings: %s", e)

    # 5) Markets aligned with workspace behavior
    markets_mentioned = market.get("markets_mentioned") or signal_set.get("preferred_markets") or []
    for m in (markets_mentioned[:3] if markets_mentioned else []):
        suggestions.append({
            "workspace_id": workspace_id,
            "suggestion_id": f"suggest-{uuid.uuid4().hex[:10]}",
            "suggested_research_direction": f"Research market: {m}",
            "direction_type": SUGGESTION_MARKET_ALIGNED,
            "supporting_signals": {"source": "market_activity", "market": m},
            "reasoning_summary": f"Market {m} aligns with workspace activity; worth investigating.",
            "timestamp": _ts(),
        })

    # 6) Follow-up research directions (from prior sessions)
    try:
        from amazon_research.discovery.copilot_research_memory import list_sessions
        sessions = list_sessions(workspace_id=workspace_id, limit=5)
        if sessions:
            last = sessions[0]
            query = (last.get("copilot_query") or "").strip()
            if query:
                suggestions.append({
                    "workspace_id": workspace_id,
                    "suggestion_id": f"suggest-{uuid.uuid4().hex[:10]}",
                    "suggested_research_direction": f"Continue: {query[:60]}{'...' if len(query) > 60 else ''}",
                    "direction_type": SUGGESTION_FOLLOW_UP,
                    "supporting_signals": {"source": "prior_session", "session_id": last.get("session_id")},
                    "reasoning_summary": "Follow-up suggested from your last research session.",
                    "timestamp": _ts(),
                })
    except Exception as e:
        logger.debug("get_personalized_suggestions list_sessions: %s", e)

    # 7) From prior copilot recommendations (strategy advisor or recommendation engine)
    try:
        from amazon_research.discovery import get_recommendations
        recos = get_recommendations(workspace_id=workspace_id, limit=3)
        for r in recos[:2]:
            entity = r.get("target_entity") or {}
            ref = entity.get("ref") or entity.get("id") or ""
            if not ref:
                continue
            suggestions.append({
                "workspace_id": workspace_id,
                "suggestion_id": f"suggest-{uuid.uuid4().hex[:10]}",
                "suggested_research_direction": f"Recommended: {ref}",
                "direction_type": SUGGESTION_CLUSTER_DEEPER,
                "supporting_signals": {"source": "recommendation_engine", "ref": ref, "priority": r.get("priority_score")},
                "reasoning_summary": r.get("explanation") or f"Opportunity {ref} recommended for this workspace.",
                "timestamp": _ts(),
            })
    except Exception as e:
        logger.debug("get_personalized_suggestions get_recommendations: %s", e)

    # Dedupe by suggested_research_direction (simple string match), then cap
    seen: set = set()
    unique: List[Dict[str, Any]] = []
    for s in suggestions:
        key = (s.get("suggested_research_direction") or "")[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
    return unique[:limit]
