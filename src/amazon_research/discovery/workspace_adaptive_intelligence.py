"""
Step 159: Workspace adaptive intelligence – update workspace intelligence signals from observed behavior.
Uses recommendation loops, feed interactions, watchlist, follow-up research, copilot queries.
Produces updated preference weights for personalization, ranking, and copilot suggestions.
Lightweight, rule-based. Extensible for future ML-based adaptive intelligence.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.workspace_adaptive_intelligence")

# In-memory store: workspace_id -> latest adaptive update
_ADAPTIVE_UPDATES: Dict[int, Dict[str, Any]] = {}

# Default boost for reinforced entities (rule-based multiplier)
DEFAULT_REINFORCED_WEIGHT = 1.2
DEFAULT_NEUTRAL_WEIGHT = 1.0


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_adaptive_update(
    workspace_id: int,
    *,
    loop_signals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compute adaptive signal update from recommendation loops, workspace intelligence, and behavior.
    Returns: workspace_id, adaptive_signal_update_id, updated_preference_weights,
    reinforcement_signals_used, timestamp. Updates are stored for get_adaptive_preference_weights.
    """
    update_id = f"adaptive-{uuid.uuid4().hex[:12]}"
    now = _ts()

    # 1) Recommendation loop reinforcement
    if loop_signals is None:
        try:
            from amazon_research.discovery import get_loop_reinforcement_signals
            loop_signals = get_loop_reinforcement_signals(workspace_id, limit=100)
        except Exception as e:
            logger.debug("compute_adaptive_update get_loop_reinforcement_signals: %s", e)
            loop_signals = {}
    reinforced_refs = list(loop_signals.get("reinforced_entity_refs") or [])[:30]
    by_action = dict(loop_signals.get("reinforcement_by_action_type") or {})
    total_loops = loop_signals.get("total_loops") or 0

    # 2) Optional: workspace intelligence / personalization baseline (for context)
    baseline_niches: List[str] = []
    try:
        from amazon_research.monitoring import get_workspace_intelligence, get_workspace_personalization_signals
        intel = get_workspace_intelligence(workspace_id)
        focus = intel.get("focus_areas_summary") or {}
        baseline_niches = list(focus.get("top_niche_cluster_terms") or [])[:15]
        personalization = get_workspace_personalization_signals(workspace_id, intelligence_output=intel)
        signal_set = personalization.get("personalization_signal_set") or {}
        if not baseline_niches:
            baseline_niches = list(signal_set.get("preferred_niche_types") or [])[:15]
    except Exception as e:
        logger.debug("compute_adaptive_update intelligence/personalization: %s", e)

    # 3) Rule-based updated preference weights
    preferred_niche_weights: Dict[str, float] = {}
    for ref in baseline_niches:
        preferred_niche_weights[str(ref)] = DEFAULT_NEUTRAL_WEIGHT
    for ref in reinforced_refs:
        r = str(ref).strip()
        if r:
            preferred_niche_weights[r] = DEFAULT_REINFORCED_WEIGHT
    if not preferred_niche_weights and reinforced_refs:
        for ref in reinforced_refs[:20]:
            preferred_niche_weights[str(ref)] = DEFAULT_REINFORCED_WEIGHT

    # Ranking adjustment: slight boost when we have positive loops (rule-based)
    ranking_adjustment_factor = DEFAULT_NEUTRAL_WEIGHT
    if total_loops >= 3:
        ranking_adjustment_factor = 1.05
    elif total_loops >= 1:
        ranking_adjustment_factor = 1.02

    # Suggestion priority: boost for refs that got follow_up_research or deeper_analysis
    suggestion_priority_boost: Dict[str, float] = {}
    follow_up_count = by_action.get("follow_up_research", 0) + by_action.get("deeper_analysis", 0)
    if follow_up_count > 0:
        for ref in reinforced_refs[:15]:
            suggestion_priority_boost[str(ref)] = 1.1
    updated_preference_weights: Dict[str, Any] = {
        "preferred_niche_weights": preferred_niche_weights,
        "ranking_adjustment_factor": ranking_adjustment_factor,
        "suggestion_priority_boost": suggestion_priority_boost,
    }

    # 4) Reinforcement signals used (for auditability)
    reinforcement_signals_used: Dict[str, Any] = {
        "loop_total": total_loops,
        "reinforced_entity_refs_count": len(reinforced_refs),
        "reinforcement_by_action_type": by_action,
        "baseline_niche_count": len(baseline_niches),
    }

    out: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "adaptive_signal_update_id": update_id,
        "updated_preference_weights": updated_preference_weights,
        "reinforcement_signals_used": reinforcement_signals_used,
        "timestamp": now,
    }
    _ADAPTIVE_UPDATES[workspace_id] = out
    return out


def get_adaptive_signal_update(workspace_id: int) -> Optional[Dict[str, Any]]:
    """
    Return the latest adaptive signal update for the workspace. If none exists, compute one.
    """
    if workspace_id in _ADAPTIVE_UPDATES:
        return _ADAPTIVE_UPDATES[workspace_id]
    return compute_adaptive_update(workspace_id)


def get_adaptive_preference_weights(workspace_id: int) -> Dict[str, Any]:
    """
    Return updated preference weights for use by personalization, ranking, and copilot suggestions.
    Compatible with workspace intelligence and personalized ranking/suggestions; they can apply
    these weights when computing scores or priorities. If no update exists, compute one.
    """
    update = get_adaptive_signal_update(workspace_id)
    if update and update.get("updated_preference_weights"):
        return dict(update["updated_preference_weights"])
    return {
        "preferred_niche_weights": {},
        "ranking_adjustment_factor": DEFAULT_NEUTRAL_WEIGHT,
        "suggestion_priority_boost": {},
    }
