"""
Step 238: Keyword discovery – list workspace-scoped keywords from keyword_seeds and optional opportunity context.
Reuses existing DB; no second discovery system.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from amazon_research.discovery_api.discovery_types import keyword_item

logger = get_logger("discovery_api.keyword_repository")

DEFAULT_LIMIT = 50


def list_keyword_discovery_for_workspace(
    workspace_id: Optional[int],
    q: Optional[str] = None,
    market: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    sort: str = "recent",
) -> List[Dict[str, Any]]:
    """
    Return keyword-discovery items for workspace from keyword_seeds.
    Optional filter by q (substring on keyword), market. Safe empty list on error.
    """
    if workspace_id is None:
        return []
    cap = max(1, min(limit, 200))
    try:
        from amazon_research.db import list_keyword_seeds
        seeds = list_keyword_seeds(workspace_id=workspace_id, active_only=None) or []
    except Exception as e:
        logger.warning("keyword_discovery list_keyword_seeds failed workspace_id=%s: %s", workspace_id, e)
        return []
    out: List[Dict[str, Any]] = []
    for s in seeds:
        if not isinstance(s, dict):
            continue
        keyword = (s.get("keyword") or "").strip()
        marketplace = (s.get("marketplace") or s.get("market") or "DE").strip().upper()
        if q and q.lower() not in keyword.lower():
            continue
        if market and marketplace != market.strip().upper():
            continue
        last = s.get("last_scanned_at") or s.get("updated_at")
        last_str = last.isoformat() if hasattr(last, "isoformat") else str(last) if last else None
        out.append(keyword_item(
            keyword=keyword,
            market=marketplace,
            category=None,
            result_count=0,
            opportunity_count=0,
            top_opportunity_refs=[],
            last_observed_at=last_str,
        ))
    if sort == "keyword":
        out.sort(key=lambda x: (x.get("keyword") or "").lower())
    elif sort == "market":
        out.sort(key=lambda x: (x.get("market") or "", x.get("keyword") or ""))
    else:
        out.sort(key=lambda x: x.get("last_observed_at") or "", reverse=True)
    return out[:cap]
