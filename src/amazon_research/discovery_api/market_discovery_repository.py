"""
Step 238: Market discovery – aggregate workspace-scoped markets from seeds and opportunity_memory.
Reuses existing DB; no second discovery system.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from amazon_research.discovery_api.discovery_types import market_item, KNOWN_MARKETS

logger = get_logger("discovery_api.market_repository")

DEFAULT_LIMIT = 20


def list_market_discovery_for_workspace(
    workspace_id: Optional[int],
    category: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> List[Dict[str, Any]]:
    """
    Return market-discovery items for workspace: aggregate by market from keyword_seeds,
    category_seeds, and opportunity_memory (context.market). Safe empty list on error.
    """
    if workspace_id is None:
        return []
    cap = max(1, min(limit, 50))
    try:
        from amazon_research.db import list_keyword_seeds, list_category_seeds
        from amazon_research.db import list_opportunity_memory
        kws = list_keyword_seeds(workspace_id=workspace_id) or []
        cats = list_category_seeds(workspace_id=workspace_id) or []
        opps = list_opportunity_memory(workspace_id=workspace_id, limit=500) or []
    except Exception as e:
        logger.warning("market_discovery list failed workspace_id=%s: %s", workspace_id, e)
        return []
    # Count by market
    market_counts: Dict[str, int] = {}
    market_categories: Dict[str, set] = {}
    market_opportunities: Dict[str, list] = {}
    market_last: Dict[str, str] = {}
    for s in kws:
        m = (s.get("marketplace") or s.get("market") or "DE").strip().upper() or "DE"
        market_counts[m] = market_counts.get(m, 0) + 1
        up = s.get("last_scanned_at") or s.get("updated_at")
        if up and (not market_last.get(m) or (hasattr(up, "isoformat") and str(up) > str(market_last.get(m)))):
            market_last[m] = up.isoformat() if hasattr(up, "isoformat") else str(up)
    for s in cats:
        m = (s.get("marketplace") or s.get("market") or "DE").strip().upper() or "DE"
        market_counts[m] = market_counts.get(m, 0) + 1
        url = (s.get("category_url") or "").strip()
        if url:
            market_categories.setdefault(m, set()).add(url[:100])
        up = s.get("last_scanned_at") or s.get("updated_at")
        if up and (not market_last.get(m) or (hasattr(up, "isoformat") and str(up) > str(market_last.get(m)))):
            market_last[m] = up.isoformat() if hasattr(up, "isoformat") else str(up)
    for o in opps:
        ctx = o.get("context") or {}
        m = (ctx.get("market") or ctx.get("marketplace") or "DE").strip().upper() or "DE"
        market_counts[m] = market_counts.get(m, 0) + 1
        ref = (o.get("opportunity_ref") or "").strip()
        if ref:
            market_opportunities.setdefault(m, []).append(ref)
        up = o.get("last_seen_at")
        if up and (not market_last.get(m) or (hasattr(up, "isoformat") and str(up) > str(market_last.get(m)))):
            market_last[m] = up.isoformat() if hasattr(up, "isoformat") else str(up)
    # Build ordered list: known markets first with data, then any other seen
    out: List[Dict[str, Any]] = []
    for m in KNOWN_MARKETS:
        if market_counts.get(m, 0) == 0 and not market_opportunities.get(m):
            continue
        top_cats = list(market_categories.get(m, set()))[:10]
        top_opps = list(market_opportunities.get(m, []))[:10]
        out.append(market_item(
            market_key=m,
            discovery_count=market_counts.get(m, 0),
            top_categories=top_cats,
            top_opportunities=top_opps,
            signal_summary={"seed_count": market_counts.get(m, 0)},
            last_observed_at=market_last.get(m),
        ))
    # Any other market seen in data
    for m in sorted(market_counts.keys()):
        if m in KNOWN_MARKETS:
            continue
        out.append(market_item(
            market_key=m,
            discovery_count=market_counts.get(m, 0),
            top_categories=list(market_categories.get(m, set()))[:10],
            top_opportunities=list(market_opportunities.get(m, []))[:10],
            signal_summary={"seed_count": market_counts.get(m, 0)},
            last_observed_at=market_last.get(m),
        ))
    return out[:cap]
