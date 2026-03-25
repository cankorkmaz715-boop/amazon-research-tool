"""
Steps 246–248: Opportunity trend timeline. Uses persistence history (Step 236) and opportunity_memory score_history.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("opportunity_analytics.timeline")


def get_opportunity_timeline(workspace_id: int, opportunity_id: int) -> Dict[str, Any]:
    """
    Return timeline_points, score_changes, rank_changes, observed_timestamps for the opportunity.
    Uses opportunity_memory.score_history and opportunity_feed_history for this ref.
    """
    timeline_points: List[Dict[str, Any]] = []
    score_changes: List[Dict[str, Any]] = []
    rank_changes: List[Dict[str, Any]] = []
    observed_timestamps: List[str] = []
    try:
        from amazon_research.db import get_opportunity_memory_by_id
        from amazon_research.opportunity_persistence.opportunity_history_repository import list_history_for_ref
        mem = get_opportunity_memory_by_id(opportunity_id, workspace_id=workspace_id)
        if not mem:
            return {
                "timeline_points": [],
                "score_changes": [],
                "rank_changes": [],
                "observed_timestamps": [],
            }
        ref = (mem.get("opportunity_ref") or "").strip()
        score_hist = mem.get("score_history") or []
        if not isinstance(score_hist, list):
            score_hist = []

        seen_ts: set = set()
        for h in score_hist:
            if not isinstance(h, dict):
                continue
            at = h.get("at")
            score = h.get("score")
            if at:
                ts = at if isinstance(at, str) else getattr(at, "isoformat", lambda: str(at))()
                observed_timestamps.append(ts)
                seen_ts.add(ts)
                timeline_points.append({"observed_at": ts, "score": score, "rank": None})
                if score is not None:
                    score_changes.append({"at": ts, "score": score})

        if ref:
            history_rows = list_history_for_ref(workspace_id, ref, limit=100)
            for r in history_rows:
                obs = r.get("observed_at")
                ts = obs.isoformat() if hasattr(obs, "isoformat") else str(obs) if obs else None
                if not ts or ts in seen_ts:
                    continue
                seen_ts.add(ts)
                observed_timestamps.append(ts)
                payload = r.get("payload_json") or {}
                sc = payload.get("score") if isinstance(payload, dict) else None
                rk = payload.get("ranking_position") or payload.get("rank") if isinstance(payload, dict) else None
                timeline_points.append({"observed_at": ts, "score": sc, "rank": rk})
                if sc is not None:
                    score_changes.append({"at": ts, "score": sc})
                if rk is not None:
                    rank_changes.append({"at": ts, "rank": rk})

        timeline_points.sort(key=lambda x: x.get("observed_at") or "")
        observed_timestamps.sort()
    except Exception as e:
        logger.warning("get_opportunity_timeline failed workspace_id=%s opportunity_id=%s: %s", workspace_id, opportunity_id, e)

    return {
        "timeline_points": timeline_points,
        "score_changes": score_changes,
        "rank_changes": rank_changes,
        "observed_timestamps": observed_timestamps,
    }
