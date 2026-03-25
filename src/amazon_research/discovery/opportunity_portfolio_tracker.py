"""
Step 175: Opportunity portfolio tracker – workspace-level portfolio tracking layer.
Tracks: watched opportunities, predictive watch candidates, active niches/clusters, rising candidates, weakening/fading.
Categories: active_watch, rising_candidate, strategic_focus, declining_item.
Integrates with predictive opportunity watch, workspace opportunity feed, opportunity memory, lifecycle engine, workspace intelligence.
Lightweight, rule-based, dashboard-friendly. Extensible for portfolio strategy analytics.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_portfolio_tracker")

# Portfolio categories (portfolio_status)
STATUS_ACTIVE_WATCH = "active_watch"
STATUS_RISING_CANDIDATE = "rising_candidate"
STATUS_STRATEGIC_FOCUS = "strategic_focus"
STATUS_DECLINING_ITEM = "declining_item"

PORTFOLIO_STATUSES = [
    STATUS_ACTIVE_WATCH,
    STATUS_RISING_CANDIDATE,
    STATUS_STRATEGIC_FOCUS,
    STATUS_DECLINING_ITEM,
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _portfolio_item(
    workspace_id: int,
    target_entity_ref: str,
    portfolio_status: str,
    short_signal_summary: str,
    target_entity_type: str = "opportunity",
    **extra: Any,
) -> Dict[str, Any]:
    return {
        "workspace_id": workspace_id,
        "portfolio_item_id": f"port-{uuid.uuid4().hex[:12]}",
        "target_entity": {"ref": target_entity_ref, "type": target_entity_type},
        "portfolio_status": portfolio_status,
        "short_signal_summary": (short_signal_summary or "").strip() or portfolio_status.replace("_", " "),
        "timestamp": _now_iso(),
        **extra,
    }


def get_workspace_portfolio(
    workspace_id: int,
    limit: int = 100,
    include_watchlist: bool = True,
    include_predictive: bool = True,
    include_lifecycle_declining: bool = True,
    include_intelligence_focus: bool = True,
) -> List[Dict[str, Any]]:
    """
    Build workspace portfolio: watched opportunities, predictive watch candidates, rising candidates, declining items.
    Returns list of { workspace_id, portfolio_item_id, target_entity, portfolio_status, short_signal_summary, timestamp }.
    Deduplicates by target_entity ref; prefers rising_candidate > strategic_focus > active_watch > declining_item.
    """
    items: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    priority_order = {STATUS_RISING_CANDIDATE: 0, STATUS_STRATEGIC_FOCUS: 1, STATUS_ACTIVE_WATCH: 2, STATUS_DECLINING_ITEM: 3}

    def add_item(ref: str, status: str, summary: str, entity_type: str = "opportunity", **kw: Any) -> None:
        ref = (ref or "").strip()
        if not ref:
            return
        if ref in seen:
            # Replace if new status has higher priority
            for i, it in enumerate(items):
                if (it.get("target_entity") or {}).get("ref") == ref:
                    if priority_order.get(status, 99) < priority_order.get(it.get("portfolio_status"), 99):
                        items[i] = _portfolio_item(workspace_id, ref, status, summary, target_entity_type=entity_type, **kw)
                    return
            return
        seen.add(ref)
        items.append(_portfolio_item(workspace_id, ref, status, summary, target_entity_type=entity_type, **kw))

    # 1) Watchlist intelligence -> active_watch or strategic_focus
    if include_watchlist:
        try:
            from amazon_research.discovery import list_watch_intelligence
            for w in list_watch_intelligence(workspace_id, limit=limit // 2):
                ref = (w.get("watched_entity") or w.get("target_entity") or "").strip()
                if not ref and isinstance(w.get("target_entity"), dict):
                    ref = (w.get("target_entity") or {}).get("ref") or ""
                label = (w.get("watch_intelligence_label") or "").strip().lower()
                importance = w.get("importance_score") or 0
                if label == "high_priority":
                    add_item(ref, STATUS_STRATEGIC_FOCUS, f"Watchlist high priority (score {importance}).", "opportunity")
                else:
                    add_item(ref, STATUS_ACTIVE_WATCH, f"Watched (label: {label or 'watch'}, score {importance}).", "opportunity")
        except Exception as e:
            logger.debug("get_workspace_portfolio list_watch_intelligence: %s", e)

    # 2) Predictive watch -> rising_candidate or active_watch
    if include_predictive:
        try:
            from amazon_research.discovery import list_predictive_watch_candidates
            for row in list_predictive_watch_candidates(workspace_id=workspace_id, limit=limit // 2):
                watch = row.get("predictive_watch") or {}
                ref = (row.get("opportunity_ref") or watch.get("opportunity_id") or "").strip()
                if not ref:
                    continue
                classification = (watch.get("watch_classification") or "").strip()
                conf = watch.get("predictive_confidence") or 50
                if classification == "rising_candidate":
                    add_item(ref, STATUS_RISING_CANDIDATE, f"Rising candidate (confidence {conf}).", "opportunity")
                elif classification == "early_watch":
                    add_item(ref, STATUS_ACTIVE_WATCH, f"Early watch (confidence {conf}).", "opportunity")
                else:
                    add_item(ref, STATUS_ACTIVE_WATCH, f"Predictive watchlist (confidence {conf}).", "opportunity")
        except Exception as e:
            logger.debug("get_workspace_portfolio list_predictive_watch_candidates: %s", e)

    # 3) Lifecycle engine -> declining_item (weakening / fading)
    if include_lifecycle_declining:
        try:
            from amazon_research.discovery import list_opportunities_with_lifecycle_engine
            for row in list_opportunities_with_lifecycle_engine(workspace_id=workspace_id, limit=limit // 2):
                life = row.get("lifecycle_engine") or row
                ref = (row.get("opportunity_ref") or life.get("opportunity_id") or "").strip()
                state = (life.get("lifecycle_state") or "").strip().lower()
                if state in ("weakening", "fading"):
                    add_item(ref, STATUS_DECLINING_ITEM, f"Lifecycle {state}.", "opportunity")
        except Exception as e:
            logger.debug("get_workspace_portfolio list_opportunities_with_lifecycle_engine: %s", e)

    # 4) Workspace intelligence focus areas -> strategic_focus (niches/clusters)
    if include_intelligence_focus:
        try:
            from amazon_research.monitoring import get_workspace_intelligence
            intel = get_workspace_intelligence(workspace_id)
            focus_summary = intel.get("focus_areas_summary") or {}
            focus = (focus_summary.get("top_niche_cluster_terms") or [])[:10]
            if isinstance(focus, list):
                for f in focus:
                    ref = f if isinstance(f, str) else (f.get("ref") or f.get("niche") or f.get("cluster") or "")
                    if ref:
                        add_item(str(ref), STATUS_STRATEGIC_FOCUS, "Workspace focus area.", "cluster")
        except Exception as e:
            logger.debug("get_workspace_portfolio get_workspace_intelligence: %s", e)

    # Sort: rising first, then strategic_focus, active_watch, declining last
    def sort_key(it: Dict[str, Any]) -> int:
        return priority_order.get(it.get("portfolio_status"), 99)

    items.sort(key=sort_key)
    return items[:limit]


def get_portfolio_summary(workspace_id: int, limit: int = 100) -> Dict[str, Any]:
    """
    Return portfolio counts by status and timestamp. Dashboard-friendly summary.
    """
    items = get_workspace_portfolio(workspace_id, limit=limit)
    by_status: Dict[str, int] = {}
    for it in items:
        s = it.get("portfolio_status") or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "workspace_id": workspace_id,
        "total_items": len(items),
        "by_status": by_status,
        "timestamp": _now_iso(),
    }
