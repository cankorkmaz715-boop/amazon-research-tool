"""
Step 156: Workspace intelligence timeline – present important workspace intelligence events over time.
Aggregates from opportunity feed, lifecycle, alerts, watchlist, copilot suggestions, research actions.
Rule-based, dashboard-friendly. Extensible for timeline filters and historical views.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.workspace_intelligence_timeline")

# Timeline event types
EVENT_NEW_OPPORTUNITY = "new_opportunity"
EVENT_RISING_OPPORTUNITY = "rising_opportunity"
EVENT_WEAKENING_OPPORTUNITY = "weakening_opportunity"
EVENT_ALERT = "alert_event"
EVENT_WATCHLIST = "watchlist_event"
EVENT_COPILOT_SUGGESTION = "copilot_suggestion"
EVENT_RESEARCH_ACTION = "research_action"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timeline_event(
    workspace_id: int,
    event_type: str,
    target_entity: Dict[str, Any],
    short_summary: str,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a single timeline entry."""
    return {
        "workspace_id": workspace_id,
        "timeline_event_id": f"timeline-{uuid.uuid4().hex[:12]}",
        "event_type": event_type,
        "target_entity": target_entity if isinstance(target_entity, dict) else {"type": "cluster", "ref": str(target_entity)},
        "short_summary": (short_summary or "").strip() or event_type.replace("_", " "),
        "timestamp": timestamp or _ts(),
    }


def get_workspace_intelligence_timeline(
    workspace_id: int,
    *,
    limit: int = 100,
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build workspace intelligence timeline from feed, lifecycle, alerts, watchlist,
    copilot suggestions, and research action queue. Returns list of timeline entries:
    workspace_id, timeline_event_id, event_type, target_entity, short_summary, timestamp.
    Sorted by timestamp descending (newest first). Optional since filter for future use.
    """
    events: List[Dict[str, Any]] = []
    now_ts = _ts()

    # 1) Workspace opportunity feed -> new_opportunity, rising_opportunity, weakening_opportunity, watchlist_event, copilot_suggestion
    try:
        from amazon_research.discovery import get_workspace_opportunity_feed
        feed = get_workspace_opportunity_feed(workspace_id, limit=limit)
        for it in feed:
            te = it.get("target_entity") or {}
            feed_type = it.get("feed_item_type", "")
            if feed_type == "new_opportunity":
                events.append(_timeline_event(
                    workspace_id, EVENT_NEW_OPPORTUNITY,
                    te, it.get("short_explanation") or "New opportunity.", it.get("timestamp") or now_ts,
                ))
            elif feed_type == "rising_opportunity":
                events.append(_timeline_event(
                    workspace_id, EVENT_RISING_OPPORTUNITY,
                    te, it.get("short_explanation") or "Rising opportunity.", it.get("timestamp") or now_ts,
                ))
            elif feed_type == "risky_opportunity":
                events.append(_timeline_event(
                    workspace_id, EVENT_WEAKENING_OPPORTUNITY,
                    te, it.get("short_explanation") or "Risky/weakening opportunity.", it.get("timestamp") or now_ts,
                ))
            elif feed_type == "watchlist_update":
                events.append(_timeline_event(
                    workspace_id, EVENT_WATCHLIST,
                    te, it.get("short_explanation") or "Watchlist update.", it.get("timestamp") or now_ts,
                ))
            elif feed_type == "suggested_next_action":
                events.append(_timeline_event(
                    workspace_id, EVENT_COPILOT_SUGGESTION,
                    te, it.get("short_explanation") or "Copilot suggestion.", it.get("timestamp") or now_ts,
                ))
    except Exception as e:
        logger.debug("get_workspace_intelligence_timeline feed: %s", e)

    # 2) Opportunity lifecycle -> rising / weakening events (add if not duplicating feed)
    try:
        from amazon_research.discovery import list_opportunities_with_lifecycle
        for life in list_opportunities_with_lifecycle(limit=15, workspace_id=workspace_id):
            ref = life.get("opportunity_id")
            state = (life.get("lifecycle_state") or "").strip().lower()
            if not ref:
                continue
            te = {"type": "cluster", "ref": ref}
            if state in ("rising", "stable", "new"):
                events.append(_timeline_event(
                    workspace_id, EVENT_RISING_OPPORTUNITY,
                    te, life.get("rationale") or f"Lifecycle: {state}.", now_ts,
                ))
            elif state in ("weakening", "fading"):
                events.append(_timeline_event(
                    workspace_id, EVENT_WEAKENING_OPPORTUNITY,
                    te, life.get("rationale") or f"Lifecycle: {state}.", now_ts,
                ))
    except Exception as e:
        logger.debug("get_workspace_intelligence_timeline lifecycle: %s", e)

    # 3) Alert prioritization -> alert_event
    try:
        from amazon_research.discovery import get_prioritized_alerts
        for alert in get_prioritized_alerts(workspace_id=workspace_id, limit_opportunity=10, limit_watch=10, include_operational=False):
            sig = alert.get("signal_summary") or {}
            ref = sig.get("target_entity") or sig.get("watched_entity") or alert.get("alert_id") or ""
            if isinstance(ref, dict):
                ref = ref.get("ref") or str(ref)
            te = {"type": "cluster", "ref": str(ref)} if ref else {"type": "alert", "ref": str(alert.get("alert_id", ""))}
            events.append(_timeline_event(
                workspace_id, EVENT_ALERT,
                te, f"Alert: {alert.get('priority_label', 'update')} (score {alert.get('priority_score', 0):.0f}).",
                alert.get("timestamp") or now_ts,
            ))
    except Exception as e:
        logger.debug("get_workspace_intelligence_timeline alerts: %s", e)

    # 4) Watchlist intelligence -> watchlist_event
    try:
        from amazon_research.discovery import list_watch_intelligence
        for w in list_watch_intelligence(workspace_id, limit=10):
            ref = w.get("watched_entity") or w.get("watch_id") or ""
            te = {"type": "cluster", "ref": str(ref)}
            events.append(_timeline_event(
                workspace_id, EVENT_WATCHLIST,
                te, w.get("detected_change_summary") or "Watchlist update.", now_ts,
            ))
    except Exception as e:
        logger.debug("get_workspace_intelligence_timeline watchlist: %s", e)

    # 5) Copilot suggestions -> copilot_suggestion
    try:
        from amazon_research.discovery import get_personalized_suggestions
        for s in get_personalized_suggestions(workspace_id, limit=10):
            direction = (s.get("suggested_research_direction") or "").strip()
            if not direction:
                continue
            te = {"type": "niche", "ref": direction[:200]}
            events.append(_timeline_event(
                workspace_id, EVENT_COPILOT_SUGGESTION,
                te, s.get("reasoning_summary") or direction[:150], s.get("timestamp") or now_ts,
            ))
    except Exception as e:
        logger.debug("get_workspace_intelligence_timeline suggestions: %s", e)

    # 6) Research action queue -> research_action
    try:
        from amazon_research.discovery import get_action_queue
        for act in get_action_queue(workspace_id=workspace_id, limit_recommendations=15, limit_actions=20):
            entity = act.get("target_entity") or {}
            ref = (entity.get("ref") or "").strip() or act.get("action_id", "")
            te = {"type": entity.get("type") or "cluster", "ref": str(ref)}
            events.append(_timeline_event(
                workspace_id, EVENT_RESEARCH_ACTION,
                te, act.get("rationale") or f"Suggested action: {act.get('action_type', 'action')}.", act.get("timestamp") or now_ts,
            ))
    except Exception as e:
        logger.debug("get_workspace_intelligence_timeline action_queue: %s", e)

    # Dedupe by (event_type, target_entity.ref) keeping first (we'll sort by timestamp so "first" is arbitrary; prefer keeping one per key)
    by_key: Dict[tuple, Dict[str, Any]] = {}
    for ev in events:
        ref = (ev.get("target_entity") or {}).get("ref") or ""
        key = (ev.get("event_type", ""), (ref or ev.get("short_summary", ""))[:150])
        if key not in by_key:
            by_key[key] = ev
    ordered = list(by_key.values())
    if since:
        ordered = [e for e in ordered if (e.get("timestamp") or "") >= since]
    ordered.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return ordered[:limit]
