"""
Steps 243–245: Category opportunity explorer. Workspace-scoped.
Returns category, opportunity_count, keyword_count, top_opportunities, top_keywords.
"""
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("research_intelligence.category_explorer")

TOP_N = 10


def _explorer_item(
    category: str,
    opportunity_count: int = 0,
    keyword_count: int = 0,
    top_opportunities: List[str] = None,
    top_keywords: List[str] = None,
) -> Dict[str, Any]:
    return {
        "category": (category or "")[:200],
        "opportunity_count": max(0, opportunity_count),
        "keyword_count": max(0, keyword_count),
        "top_opportunities": list(top_opportunities or [])[:TOP_N],
        "top_keywords": list(top_keywords or [])[:TOP_N],
    }


def get_category_explorer(workspace_id: int) -> List[Dict[str, Any]]:
    """Return category explorer items: category, counts, top lists. Workspace-scoped."""
    out: List[Dict[str, Any]] = []
    try:
        from amazon_research.db import list_category_seeds, list_opportunity_memory
        categories = list_category_seeds(workspace_id=workspace_id, active_only=None) or []
        opportunities = list_opportunity_memory(workspace_id=workspace_id, limit=500) or []
    except Exception as e:
        logger.warning("get_category_explorer failed workspace_id=%s: %s", workspace_id, e)
        return []

    by_cat_opp: Dict[str, List[str]] = {}
    by_cat_kw: Dict[str, List[str]] = {}
    for c in categories:
        if not isinstance(c, dict):
            continue
        cat = (c.get("category_url") or c.get("label") or "").strip() or "unknown"
        by_cat_opp.setdefault(cat, [])
        by_cat_kw.setdefault(cat, [])
    for o in opportunities:
        if not isinstance(o, dict):
            continue
        ctx = o.get("context") or {}
        cat = (ctx.get("category") or ctx.get("category_url") or "").strip() or "uncategorized"
        ref = (o.get("opportunity_ref") or "").strip()
        if ref:
            by_cat_opp.setdefault(cat, []).append(ref)
    for cat in list(by_cat_opp.keys()):
        if cat == "uncategorized" and not by_cat_opp[cat]:
            continue
        out.append(_explorer_item(
            category=cat,
            opportunity_count=len(by_cat_opp.get(cat, [])),
            keyword_count=len(by_cat_kw.get(cat, [])),
            top_opportunities=by_cat_opp.get(cat, [])[:TOP_N],
            top_keywords=by_cat_kw.get(cat, [])[:TOP_N],
        ))
    out.sort(key=lambda x: (x["opportunity_count"], x["category"]), reverse=True)
    return out
