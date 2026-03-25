"""
Steps 243–245: Keyword opportunity clustering. Deterministic, workspace-scoped.
Cluster by market: cluster_id = market, keyword_count, opportunity_count, top_keywords, top_opportunities.
"""
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("research_intelligence.clusters")

KNOWN_MARKETS = ("DE", "US", "AU")
TOP_N = 10


def _cluster_item(
    cluster_id: str,
    cluster_label: str,
    keyword_count: int = 0,
    opportunity_count: int = 0,
    top_keywords: List[str] = None,
    top_opportunities: List[str] = None,
) -> Dict[str, Any]:
    return {
        "cluster_id": (cluster_id or "")[:50],
        "cluster_label": (cluster_label or "")[:100],
        "keyword_count": max(0, keyword_count),
        "opportunity_count": max(0, opportunity_count),
        "top_keywords": list(top_keywords or [])[:TOP_N],
        "top_opportunities": list(top_opportunities or [])[:TOP_N],
    }


def get_clusters(workspace_id: int) -> List[Dict[str, Any]]:
    """Return keyword/opportunity clusters grouped by market. Deterministic, workspace-scoped."""
    out: List[Dict[str, Any]] = []
    try:
        from amazon_research.db import list_keyword_seeds, list_opportunity_memory
        keywords = list_keyword_seeds(workspace_id=workspace_id, active_only=None) or []
        opportunities = list_opportunity_memory(workspace_id=workspace_id, limit=500) or []
    except Exception as e:
        logger.warning("get_clusters failed workspace_id=%s: %s", workspace_id, e)
        return []

    by_market_kw: Dict[str, List[str]] = {}
    by_market_opp: Dict[str, List[str]] = {}
    for s in keywords:
        if not isinstance(s, dict):
            continue
        m = (s.get("marketplace") or s.get("market") or "DE").strip().upper() or "DE"
        kw = (s.get("keyword") or "").strip()
        if kw:
            by_market_kw.setdefault(m, []).append(kw)
    for o in opportunities:
        if not isinstance(o, dict):
            continue
        ctx = o.get("context") or {}
        m = (ctx.get("market") or ctx.get("marketplace") or "DE").strip().upper() or "DE"
        ref = (o.get("opportunity_ref") or "").strip()
        if ref:
            by_market_opp.setdefault(m, []).append(ref)

    for m in KNOWN_MARKETS:
        kws = by_market_kw.get(m, [])
        opps = by_market_opp.get(m, [])
        if not kws and not opps:
            continue
        out.append(_cluster_item(
            cluster_id=m,
            cluster_label=m,
            keyword_count=len(kws),
            opportunity_count=len(opps),
            top_keywords=kws[:TOP_N],
            top_opportunities=opps[:TOP_N],
        ))
    for m in sorted(by_market_kw.keys()):
        if m in KNOWN_MARKETS:
            continue
        kws = by_market_kw.get(m, [])
        opps = by_market_opp.get(m, [])
        out.append(_cluster_item(
            cluster_id=m,
            cluster_label=m,
            keyword_count=len(kws),
            opportunity_count=len(opps),
            top_keywords=kws[:TOP_N],
            top_opportunities=opps[:TOP_N],
        ))
    return out
