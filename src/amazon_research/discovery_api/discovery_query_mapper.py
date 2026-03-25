"""
Step 238: Validate and map discovery query params. Strict and safe defaults.
"""
from typing import Any, Dict, Optional

from amazon_research.discovery_api.discovery_types import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MAX_QUERY_LEN,
    ALLOWED_SORT,
    KNOWN_MARKETS,
)


def parse_keyword_params(
    q: Optional[str] = None,
    market: Optional[str] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
) -> Dict[str, Any]:
    """Return validated params for keyword discovery. Safe defaults."""
    query = (q or "").strip()[:MAX_QUERY_LEN]
    market_clean = (market or "").strip().upper()
    if market_clean and market_clean not in KNOWN_MARKETS:
        market_clean = ""
    lim = DEFAULT_LIMIT
    if limit is not None:
        try:
            lim = max(1, min(int(limit), MAX_LIMIT))
        except (TypeError, ValueError):
            pass
    sort_clean = (sort or "recent").strip().lower()
    if sort_clean not in ALLOWED_SORT:
        sort_clean = "recent"
    return {
        "q": query,
        "market": market_clean or None,
        "limit": lim,
        "sort": sort_clean,
    }


def parse_market_params(
    category: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Return validated params for market discovery."""
    category_clean = (category or "").strip()[:MAX_QUERY_LEN] or None
    lim = DEFAULT_LIMIT
    if limit is not None:
        try:
            lim = max(1, min(int(limit), MAX_LIMIT))
        except (TypeError, ValueError):
            pass
    return {
        "category": category_clean,
        "limit": lim,
    }
