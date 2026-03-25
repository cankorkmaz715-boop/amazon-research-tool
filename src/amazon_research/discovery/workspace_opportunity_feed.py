"""
Step 155: Workspace opportunity feed – aggregate workspace-relevant research outputs into a unified feed.
Combines personalized ranking, watchlist intelligence, alert prioritization, lifecycle, confidence,
explainability, and personalized copilot suggestions. Rule-based, dashboard-friendly. Extensible for real-time feeds.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.workspace_opportunity_feed")

# Feed item types
FEED_NEW_OPPORTUNITY = "new_opportunity"
FEED_RISING_OPPORTUNITY = "rising_opportunity"
FEED_RISKY_OPPORTUNITY = "risky_opportunity"
FEED_WATCHLIST_UPDATE = "watchlist_update"
FEED_SUGGESTED_NEXT_ACTION = "suggested_next_action"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entity_type(ref: str) -> str:
    """Infer target entity type from ref string (asin / niche / cluster / keyword)."""
    if not ref or not isinstance(ref, str):
        return "cluster"
    r = ref.strip().lower()
    # ASIN-like: 10 alphanumeric
    if re.match(r"^[a-z0-9]{10}$", r):
        return "asin"
    if "niche:" in r or r.startswith("niche-"):
        return "niche"
    if "keyword:" in r or r.startswith("kw-") or "keyword" in r:
        return "keyword"
    if "cluster:" in r or r.startswith("cluster-") or "cluster" in r:
        return "cluster"
    return "cluster"


def _feed_item(
    workspace_id: int,
    feed_type: str,
    target_ref: str,
    entity_type: Optional[str] = None,
    priority_score: float = 50.0,
    short_explanation: str = "",
) -> Dict[str, Any]:
    """Build a single feed entry with required fields."""
    return {
        "workspace_id": workspace_id,
        "feed_item_id": f"feed-{uuid.uuid4().hex[:12]}",
        "target_entity": {"type": entity_type or _entity_type(target_ref), "ref": target_ref},
        "feed_item_type": feed_type,
        "priority_score": round(min(100.0, max(0.0, float(priority_score))), 1),
        "short_explanation": (short_explanation or "").strip() or f"{feed_type.replace('_', ' ')}.",
        "timestamp": _ts(),
    }


def get_workspace_opportunity_feed(
    workspace_id: int,
    *,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Build workspace-specific opportunity feed from personalized ranking, watchlist intelligence,
    alert prioritization, lifecycle, confidence, explainability, and personalized suggestions.
    Returns list of feed entries: workspace_id, feed_item_id, target_entity, feed_item_type,
    priority_score, short_explanation, timestamp. Sorted by priority_score descending.
    """
    items: List[Dict[str, Any]] = []

    # 1) Personalized opportunity ranking -> new / rising opportunities
    try:
        from amazon_research.discovery import list_personalized_rankings, list_opportunities_with_lifecycle
        rankings = list_personalized_rankings(workspace_id, limit=15)
        life_map: Dict[str, str] = {}
        for life in list_opportunities_with_lifecycle(limit=20, workspace_id=workspace_id):
            ref = life.get("opportunity_id")
            if ref:
                life_map[str(ref)] = (life.get("lifecycle_state") or "").strip().lower()
        for r in rankings[:10]:
            ref = r.get("target_opportunity_id") or ""
            if not ref:
                continue
            score = r.get("personalized_score") or 0.0
            state = life_map.get(ref, "")
            if state in ("new",):
                items.append(_feed_item(
                    workspace_id, FEED_NEW_OPPORTUNITY, ref,
                    priority_score=score,
                    short_explanation=r.get("personalization_explanation") or f"New opportunity (score {score:.0f}).",
                ))
            elif state in ("rising", "stable") and score >= 50:
                items.append(_feed_item(
                    workspace_id, FEED_RISING_OPPORTUNITY, ref,
                    priority_score=score,
                    short_explanation=r.get("personalization_explanation") or f"Rising/stable opportunity (score {score:.0f}).",
                ))
    except Exception as e:
        logger.debug("get_workspace_opportunity_feed personalized/lifecycle: %s", e)

    # 2) Opportunity lifecycle + confidence -> risky (weakening/fading or low confidence)
    try:
        from amazon_research.discovery import list_opportunities_with_lifecycle, list_opportunities_with_confidence
        for life in list_opportunities_with_lifecycle(limit=15, workspace_id=workspace_id):
            ref = life.get("opportunity_id")
            state = (life.get("lifecycle_state") or "").strip().lower()
            if not ref or state not in ("weakening", "fading"):
                continue
            items.append(_feed_item(
                workspace_id, FEED_RISKY_OPPORTUNITY, ref,
                priority_score=40.0,
                short_explanation=life.get("rationale") or f"Lifecycle: {state}.",
            ))
        for conf in list_opportunities_with_confidence(limit=15, workspace_id=workspace_id):
            if (conf.get("confidence_label") or "").strip().lower() != "low":
                continue
            ref = conf.get("opportunity_id")
            if not ref:
                continue
            items.append(_feed_item(
                workspace_id, FEED_RISKY_OPPORTUNITY, ref,
                priority_score=35.0,
                short_explanation=conf.get("explanation") or "Low confidence opportunity.",
            ))
    except Exception as e:
        logger.debug("get_workspace_opportunity_feed lifecycle/confidence: %s", e)

    # 3) Watchlist intelligence + alert prioritization -> watchlist_update
    try:
        from amazon_research.discovery import list_watch_intelligence, get_prioritized_alerts
        for w in list_watch_intelligence(workspace_id, limit=10):
            ref = w.get("watched_entity") or w.get("watch_id") or ""
            if not ref:
                ref = str(w.get("watch_id", ""))
            imp = w.get("importance_score") or 50.0
            summary = (w.get("detected_change_summary") or "").strip() or "Watchlist update."
            items.append(_feed_item(
                workspace_id, FEED_WATCHLIST_UPDATE, ref,
                priority_score=imp,
                short_explanation=summary,
            ))
        for alert in get_prioritized_alerts(workspace_id=workspace_id, limit_opportunity=5, limit_watch=5, include_operational=False):
            src = alert.get("alert_source", "")
            if src == "portfolio_watch":
                target = (alert.get("signal_summary") or {}).get("watched_entity") or alert.get("alert_id") or ""
                if target:
                    items.append(_feed_item(
                        workspace_id, FEED_WATCHLIST_UPDATE, str(target),
                        priority_score=alert.get("priority_score") or 50.0,
                        short_explanation=f"Alert: {alert.get('priority_label', 'update')}.",
                    ))
    except Exception as e:
        logger.debug("get_workspace_opportunity_feed watchlist/alerts: %s", e)

    # 4) Explainability: attach short explanation to existing opportunity items where missing (no new items)
    try:
        from amazon_research.discovery import list_explanations
        expl_map = {e.get("opportunity_id"): (e.get("explanation_summary") or "")[:200] for e in list_explanations(limit=25, workspace_id=workspace_id) if e.get("opportunity_id")}
        for it in items:
            ref = (it.get("target_entity") or {}).get("ref")
            if ref and expl_map.get(ref) and not (it.get("short_explanation") or "").strip():
                it["short_explanation"] = expl_map[ref]
    except Exception as e:
        logger.debug("get_workspace_opportunity_feed explainability: %s", e)

    # 5) Personalized copilot suggestions -> suggested_next_action
    try:
        from amazon_research.discovery import get_personalized_suggestions
        for s in get_personalized_suggestions(workspace_id, limit=10):
            direction = (s.get("suggested_research_direction") or "").strip()
            if not direction:
                continue
            # Use direction as ref for suggested actions (entity type = niche as generic)
            items.append(_feed_item(
                workspace_id, FEED_SUGGESTED_NEXT_ACTION, direction,
                entity_type="niche",
                priority_score=55.0,
                short_explanation=s.get("reasoning_summary") or direction[:150],
            ))
    except Exception as e:
        logger.debug("get_workspace_opportunity_feed suggestions: %s", e)

    # Dedupe by (feed_item_type, target_entity.ref) keeping highest priority
    by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for it in items:
        ref = (it.get("target_entity") or {}).get("ref") or ""
        key = (it.get("feed_item_type", ""), ref[:200])
        if key not in by_key or (it.get("priority_score") or 0) > (by_key[key].get("priority_score") or 0):
            by_key[key] = it
    ordered = list(by_key.values())
    ordered.sort(key=lambda x: (x.get("priority_score") or 0.0), reverse=True)
    return ordered[:limit]
