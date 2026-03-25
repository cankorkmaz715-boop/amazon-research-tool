"""
Step 151: SaaS workspace intelligence layer – analyze behavior and research patterns at the workspace level.
Derives focus areas, market activity, research behavior, and notable patterns from copilot memory,
threading, watchlist, recommendations, and workspace analytics. Rule-based, explainable.
"""
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.workspace_intelligence")

# Market hints (from query text)
MARKET_PATTERNS = [
    (r"\b(?:us|usa|united states)\b", "US"),
    (r"\b(?:uk|gb|united kingdom)\b", "UK"),
    (r"\b(?:de|germany)\b", "DE"),
    (r"\bamazon\.com\b", "US"),
    (r"\bamazon\.co\.uk\b", "UK"),
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_markets_from_text(text: str) -> List[str]:
    """Extract market hints from free text. Rule-based."""
    if not text:
        return []
    t = text.lower()
    found: List[str] = []
    for pattern, market in MARKET_PATTERNS:
        if re.search(pattern, t, re.IGNORECASE):
            if market not in found:
                found.append(market)
    return found


def _extract_niche_cluster_hints(text: str) -> List[str]:
    """Extract likely niche/cluster keywords from query or topic (simple word chunks)."""
    if not text or len(text) < 2:
        return []
    # Drop common words; keep potential focus terms (simple heuristic)
    stop = {"find", "niches", "niche", "in", "for", "explore", "keywords", "market", "research", "analyze", "product", "cluster", "the", "a", "and", "or"}
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in stop and len(w) > 2][:15]


def get_workspace_intelligence(
    workspace_id: int,
    *,
    limit_sessions: int = 50,
    limit_threads: int = 30,
    limit_watches: int = 100,
    limit_recommendations: int = 30,
) -> Dict[str, Any]:
    """
    Analyze workspace-level behavior and research patterns. Returns: workspace_id,
    focus_areas_summary, market_activity_summary, research_behavior_summary,
    notable_patterns_or_tendencies, timestamp.
    """
    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "focus_areas_summary": {},
        "market_activity_summary": {},
        "research_behavior_summary": {},
        "notable_patterns_or_tendencies": [],
        "timestamp": _ts(),
    }

    sessions: List[Dict[str, Any]] = []
    threads: List[Dict[str, Any]] = []
    watches: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []
    usage_dashboard: Optional[Dict[str, Any]] = None

    try:
        from amazon_research.discovery.copilot_research_memory import list_sessions
        sessions = list_sessions(workspace_id=workspace_id, limit=limit_sessions)
    except Exception as e:
        logger.debug("get_workspace_intelligence list_sessions: %s", e)

    try:
        from amazon_research.discovery.conversational_threading import list_threads
        threads = list_threads(workspace_id=workspace_id, limit=limit_threads)
    except Exception as e:
        logger.debug("get_workspace_intelligence list_threads: %s", e)

    try:
        from amazon_research.db import list_watches
        watches = list_watches(workspace_id=workspace_id, limit=limit_watches)
    except Exception as e:
        logger.debug("get_workspace_intelligence list_watches: %s", e)

    try:
        from amazon_research.discovery.recommendation_engine import get_recommendations
        recommendations = get_recommendations(workspace_id=workspace_id, limit=limit_recommendations)
    except Exception as e:
        logger.debug("get_workspace_intelligence get_recommendations: %s", e)

    try:
        from amazon_research.monitoring.workspace_usage_dashboard import get_workspace_usage_dashboard
        usage_dashboard = get_workspace_usage_dashboard(workspace_id)
    except Exception as e:
        logger.debug("get_workspace_intelligence get_workspace_usage_dashboard: %s", e)

    # --- Focus areas summary (niche/cluster from sessions, threads, watches) ---
    niche_cluster_mentions: List[str] = []
    for s in sessions:
        q = (s.get("copilot_query") or "").strip()
        niche_cluster_mentions.extend(_extract_niche_cluster_hints(q))
    for t in threads:
        topic = (t.get("thread_topic") or "").strip()
        anchor = (t.get("thread_anchor") or "").strip()
        niche_cluster_mentions.extend(_extract_niche_cluster_hints(f"{topic} {anchor}"))
    watch_targets: Dict[str, List[str]] = {}
    for w in watches:
        ttype = (w.get("target_type") or "cluster").strip().lower()
        ref = (w.get("target_ref") or "").strip()
        if ref:
            watch_targets.setdefault(ttype, []).append(ref)
            if ttype in ("niche", "cluster"):
                niche_cluster_mentions.append(ref)
    focus_counter = Counter(niche_cluster_mentions)
    out["focus_areas_summary"] = {
        "top_niche_cluster_terms": [x[0] for x in focus_counter.most_common(10)],
        "watchlist_by_type": {k: len(v) for k, v in watch_targets.items()},
        "session_count": len(sessions),
        "thread_count": len(threads),
    }

    # --- Market activity summary ---
    markets_seen: List[str] = []
    for s in sessions:
        markets_seen.extend(_extract_markets_from_text(s.get("copilot_query") or ""))
    for t in threads:
        markets_seen.extend(_extract_markets_from_text(t.get("thread_topic") or ""))
        markets_seen.extend(_extract_markets_from_text(t.get("thread_anchor") or ""))
    market_counts = Counter(markets_seen)
    out["market_activity_summary"] = {
        "markets_mentioned": list(market_counts.keys()),
        "mention_counts": dict(market_counts),
        "session_queries_with_market": len([s for s in sessions if _extract_markets_from_text(s.get("copilot_query") or "")]),
    }

    # --- Research behavior summary ---
    intent_counts = Counter((s.get("interpreted_intent") or "unknown") for s in sessions)
    rec_entity_types = Counter()
    for r in recommendations:
        entity = r.get("target_entity") or {}
        t = entity.get("type") or "cluster"
        rec_entity_types[t] += 1
    queue_activity = (usage_dashboard or {}).get("queue_activity") or {}
    out["research_behavior_summary"] = {
        "total_sessions": len(sessions),
        "total_threads": len(threads),
        "total_watches": len(watches),
        "intent_distribution": dict(intent_counts),
        "recommendation_count": len(recommendations),
        "recommendation_entity_types": dict(rec_entity_types),
        "queue_activity": queue_activity,
    }

    # --- Notable patterns or tendencies (rule-based) ---
    patterns: List[str] = []
    if len(sessions) >= 5:
        patterns.append("Multiple research sessions; active copilot usage.")
    if intent_counts.get("niche_discovery", 0) >= 2:
        patterns.append("Frequent niche discovery focus.")
    if intent_counts.get("keyword_exploration", 0) >= 2:
        patterns.append("Repeated keyword exploration.")
    if watch_targets:
        if watch_targets.get("cluster") or watch_targets.get("niche"):
            patterns.append("Watchlist focused on clusters/niches.")
        if watch_targets.get("asin"):
            patterns.append("ASIN-level watchlist usage.")
    if recommendations:
        patterns.append("Opportunity recommendations in use.")
    if market_counts:
        patterns.append(f"Market focus: {', '.join(market_counts.keys())}.")
    if len(threads) >= 2:
        patterns.append("Conversational threading in use; follow-up research.")
    out["notable_patterns_or_tendencies"] = patterns[:15]

    return out
