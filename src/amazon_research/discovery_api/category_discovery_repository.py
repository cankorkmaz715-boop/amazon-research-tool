"""
Step 238: Category discovery – list workspace-scoped categories from category_seeds.
Reuses existing DB.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from amazon_research.discovery_api.discovery_types import category_item

logger = get_logger("discovery_api.category_repository")

DEFAULT_LIMIT = 50


def list_category_discovery_for_workspace(
    workspace_id: Optional[int],
    market: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> List[Dict[str, Any]]:
    """Return category-discovery items for workspace from category_seeds. Safe empty list on error."""
    if workspace_id is None:
        return []
    cap = max(1, min(limit, 200))
    try:
        from amazon_research.db import list_category_seeds
        seeds = list_category_seeds(workspace_id=workspace_id, active_only=None) or []
    except Exception as e:
        logger.warning("category_discovery list_category_seeds failed workspace_id=%s: %s", workspace_id, e)
        return []
    out: List[Dict[str, Any]] = []
    for s in seeds:
        if not isinstance(s, dict):
            continue
        marketplace = (s.get("marketplace") or s.get("market") or "DE").strip().upper()
        if market and marketplace != market.strip().upper():
            continue
        url = (s.get("category_url") or "").strip()
        label = (s.get("label") or "").strip() or None
        last = s.get("last_scanned_at") or s.get("updated_at")
        last_str = last.isoformat() if hasattr(last, "isoformat") else str(last) if last else None
        out.append(category_item(category_url=url, market=marketplace, label=label, last_observed_at=last_str))
    out.sort(key=lambda x: (x.get("last_observed_at") or ""), reverse=True)
    return out[:cap]
