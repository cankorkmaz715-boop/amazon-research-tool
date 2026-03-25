"""
Step 238: Real market/keyword discovery API – types and limits.
"""
from typing import Any, Dict, List

# Query param limits
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MAX_QUERY_LEN = 100
ALLOWED_SORT = ("recent", "keyword", "market")

# Market keys known to the system
KNOWN_MARKETS = ("DE", "US", "AU")


def empty_keyword_result() -> Dict[str, Any]:
    return {"data": [], "meta": {"count": 0}}


def empty_market_result() -> Dict[str, Any]:
    return {"data": [], "meta": {"count": 0}}


def keyword_item(
    keyword: str,
    market: str,
    category: str = None,
    result_count: int = 0,
    opportunity_count: int = 0,
    top_opportunity_refs: List[str] = None,
    last_observed_at: str = None,
) -> Dict[str, Any]:
    return {
        "keyword": (keyword or "")[:200],
        "market": (market or "")[:20],
        "category": (category or "")[:200] if category else None,
        "result_count": max(0, result_count),
        "opportunity_count": max(0, opportunity_count),
        "top_opportunity_refs": list(top_opportunity_refs or [])[:10],
        "last_observed_at": last_observed_at,
    }


def category_item(
    category_url: str,
    market: str,
    label: str = None,
    last_observed_at: str = None,
) -> Dict[str, Any]:
    return {
        "category_url": (category_url or "")[:500],
        "market": (market or "")[:20],
        "label": (label or "")[:200] if label else None,
        "last_observed_at": last_observed_at,
    }


def empty_category_result() -> Dict[str, Any]:
    return {"data": [], "meta": {"count": 0}}


def market_item(
    market_key: str,
    discovery_count: int = 0,
    top_categories: List[str] = None,
    top_opportunities: List[str] = None,
    signal_summary: Dict[str, Any] = None,
    last_observed_at: str = None,
) -> Dict[str, Any]:
    return {
        "market_key": (market_key or "")[:20],
        "discovery_count": max(0, discovery_count),
        "top_categories": list(top_categories or [])[:10],
        "top_opportunities": list(top_opportunities or [])[:10],
        "signal_summary": dict(signal_summary or {}),
        "last_observed_at": last_observed_at,
    }


def discovery_summary(
    workspace_id: int,
    keyword_count: int = 0,
    market_count: int = 0,
    category_count: int = 0,
) -> Dict[str, Any]:
    return {
        "workspace_id": workspace_id,
        "keyword_count": max(0, keyword_count),
        "market_count": max(0, market_count),
        "category_count": max(0, category_count),
    }
