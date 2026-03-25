"""
Step 234: Real opportunity feed – load workspace-scoped opportunity_memory and rankings.
No heavy recomputation; uses existing list_opportunity_memory and get_latest_ranking.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("opportunity_feed.repository")

DEFAULT_FEED_LIMIT = 50
MAX_FEED_LIMIT = 200


def list_real_opportunities_for_workspace(
    workspace_id: Optional[int],
    limit: int = DEFAULT_FEED_LIMIT,
) -> List[Dict[str, Any]]:
    """
    Load workspace-scoped opportunity records: opportunity_memory rows plus latest ranking per ref.
    Returns list of dicts with opportunity_ref, memory row fields, and ranking (opportunity_score, etc.).
    Sorted by opportunity_score DESC, then last_seen_at DESC. Capped to limit.
    """
    if workspace_id is None:
        return []
    cap = max(1, min(limit, MAX_FEED_LIMIT))
    try:
        from amazon_research.db import list_opportunity_memory
        from amazon_research.db.opportunity_rankings import get_latest_ranking
        mem_list = list_opportunity_memory(limit=cap * 2, workspace_id=workspace_id) or []
        if not mem_list:
            return []
        out: List[Dict[str, Any]] = []
        for m in mem_list:
            ref = (m.get("opportunity_ref") or "").strip()
            if not ref:
                continue
            rank = get_latest_ranking(ref) if ref else None
            score = float(rank["opportunity_score"]) if rank and rank.get("opportunity_score") is not None else (m.get("latest_opportunity_score"))
            if score is not None:
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    score = None
            out.append({
                "opportunity_ref": ref,
                "workspace_id": workspace_id,
                "context": m.get("context") or {},
                "last_seen_at": m.get("last_seen_at"),
                "latest_opportunity_score": score,
                "status": m.get("status"),
                "ranking": rank,
            })
        def _sort_key(x: Dict[str, Any]) -> tuple:
            score = x.get("latest_opportunity_score")
            score_val = float(score) if score is not None else 0.0
            seen = x.get("last_seen_at")
            seen_val = seen.isoformat() if hasattr(seen, "isoformat") else (seen or "")
            return (score_val, seen_val)
        out.sort(key=_sort_key, reverse=True)
        return out[:cap]
    except Exception as e:
        logger.warning("opportunity_feed list_real_opportunities_for_workspace failed workspace_id=%s: %s", workspace_id, e)
        return []
