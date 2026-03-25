"""
Step 158: Workspace recommendation loops – connect recommendations/feed/suggestions to user actions and reinforce personalization.
Records which recommendations or feed items lead to follow-up research, watchlist additions, copilot queries, deeper analysis.
Produces loop reinforcement signals for future personalization. Lightweight, rule-based. Extensible for adaptive systems.
"""
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.workspace_recommendation_loops")

# User action types (resulting from a recommendation/feed/suggestion)
ACTION_FOLLOW_UP_RESEARCH = "follow_up_research"
ACTION_WATCHLIST_ADDITION = "watchlist_addition"
ACTION_COPILOT_QUERY = "copilot_query"
ACTION_DEEPER_ANALYSIS = "deeper_analysis"

# Reinforcement signal labels
REINFORCEMENT_POSITIVE = "positive"
REINFORCEMENT_NEUTRAL = "neutral"
REINFORCEMENT_NEGATIVE = "negative"

# In-memory store: workspace_id -> list of loop records (newest last for append)
_LOOPS: Dict[int, List[Dict[str, Any]]] = {}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_recommendation_loop(
    workspace_id: int,
    recommendation_id: str,
    resulting_user_action_type: str,
    *,
    loop_reinforcement_signal: Optional[str] = None,
    target_entity_ref: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Record that a recommendation (or feed item or suggestion) led to a user action.
    Returns structured output: workspace_id, recommendation_id, resulting_user_action_type,
    loop_reinforcement_signal, timestamp. Use these records to reinforce future personalization.
    """
    rec_id = (recommendation_id or "").strip() or f"loop-{uuid.uuid4().hex[:10]}"
    action_type = (resulting_user_action_type or "").strip() or ACTION_COPILOT_QUERY
    signal = (loop_reinforcement_signal or "").strip().lower() or REINFORCEMENT_POSITIVE
    if signal not in (REINFORCEMENT_POSITIVE, REINFORCEMENT_NEUTRAL, REINFORCEMENT_NEGATIVE):
        signal = REINFORCEMENT_NEUTRAL

    record: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "recommendation_id": rec_id,
        "resulting_user_action_type": action_type,
        "loop_reinforcement_signal": signal,
        "timestamp": _ts(),
    }
    if target_entity_ref is not None:
        record["target_entity_ref"] = str(target_entity_ref).strip()
    if metadata:
        record["metadata"] = dict(metadata)

    if workspace_id not in _LOOPS:
        _LOOPS[workspace_id] = []
    _LOOPS[workspace_id].append(record)
    return record


def list_recommendation_loops(
    workspace_id: int,
    *,
    limit: int = 50,
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List recorded recommendation loops for the workspace, newest first.
    Optional since (ISO timestamp) to filter.
    """
    records = _LOOPS.get(workspace_id, [])
    if since:
        records = [r for r in records if (r.get("timestamp") or "") >= since]
    records = sorted(records, key=lambda r: r.get("timestamp") or "", reverse=True)
    return records[:limit]


def get_loop_reinforcement_signals(
    workspace_id: int,
    *,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Aggregate loop records into reinforcement signals for personalization.
    Returns: workspace_id, reinforcement_by_action_type, reinforced_entity_refs (refs that got positive actions),
    total_loops, timestamp. Personalization layer can use reinforced_entity_refs to boost preferences.
    """
    records = list_recommendation_loops(workspace_id, limit=limit)
    by_action: Dict[str, int] = Counter(r.get("resulting_user_action_type") for r in records if r.get("resulting_user_action_type"))
    positive_refs: List[str] = []
    for r in records:
        if (r.get("loop_reinforcement_signal") or "").lower() == REINFORCEMENT_POSITIVE:
            ref = r.get("target_entity_ref")
            if ref and ref not in positive_refs:
                positive_refs.append(ref)

    return {
        "workspace_id": workspace_id,
        "reinforcement_by_action_type": dict(by_action),
        "reinforced_entity_refs": positive_refs[:50],
        "total_loops": len(records),
        "timestamp": _ts(),
    }


def get_loop_reinforcement_for_personalization(
    workspace_id: int,
) -> Dict[str, Any]:
    """
    Convenience: reinforcement signals in a form suitable for personalization layer.
    Returns reinforced_entity_refs and reinforcement_summary for use when computing preferences.
    """
    signals = get_loop_reinforcement_signals(workspace_id, limit=100)
    return {
        "reinforced_entity_refs": signals.get("reinforced_entity_refs", []),
        "reinforcement_by_action_type": signals.get("reinforcement_by_action_type", {}),
        "total_loops": signals.get("total_loops", 0),
    }
