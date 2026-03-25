"""
Step 238: Discovery API service – keyword and market discovery for workspace.
Reuses repositories; no heavy recomputation; safe empty-state.
"""
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

from amazon_research.discovery_api.discovery_types import (
    empty_keyword_result,
    empty_market_result,
    empty_category_result,
    discovery_summary as discovery_summary_shape,
)
from amazon_research.discovery_api.keyword_discovery_repository import list_keyword_discovery_for_workspace
from amazon_research.discovery_api.market_discovery_repository import list_market_discovery_for_workspace
from amazon_research.discovery_api.category_discovery_repository import list_category_discovery_for_workspace
from amazon_research.discovery_api.discovery_query_mapper import parse_keyword_params, parse_market_params

logger = get_logger("discovery_api.service")


def get_keyword_discovery(
    workspace_id: int,
    q: str = None,
    market: str = None,
    limit: int = None,
    sort: str = None,
) -> Dict[str, Any]:
    """
    Return keyword discovery payload for workspace. Query params validated; safe empty state.
    """
    params = parse_keyword_params(q=q, market=market, limit=limit, sort=sort)
    try:
        items = list_keyword_discovery_for_workspace(
            workspace_id=workspace_id,
            q=params.get("q") or None,
            market=params.get("market"),
            limit=params.get("limit", 50),
            sort=params.get("sort", "recent"),
        )
    except Exception as e:
        logger.warning("keyword_discovery failed workspace_id=%s: %s", workspace_id, e)
        return empty_keyword_result()
    logger.debug(
        "keyword_discovery workspace_id=%s count=%s",
        workspace_id,
        len(items),
        extra={"workspace_id": workspace_id, "count": len(items)},
    )
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


def get_market_discovery(
    workspace_id: int,
    category: str = None,
    limit: int = None,
) -> Dict[str, Any]:
    """
    Return market discovery payload for workspace. Safe empty state.
    """
    params = parse_market_params(category=category, limit=limit)
    try:
        items = list_market_discovery_for_workspace(
            workspace_id=workspace_id,
            category=params.get("category"),
            limit=params.get("limit", 20),
        )
    except Exception as e:
        logger.warning("market_discovery failed workspace_id=%s: %s", workspace_id, e)
        return empty_market_result()
    logger.debug(
        "market_discovery workspace_id=%s count=%s",
        workspace_id,
        len(items),
        extra={"workspace_id": workspace_id, "count": len(items)},
    )
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


def get_category_discovery(
    workspace_id: int,
    market: str = None,
    limit: int = None,
) -> Dict[str, Any]:
    """Return category discovery payload for workspace. Safe empty state."""
    cap = max(1, min(limit or 50, 200))
    try:
        items = list_category_discovery_for_workspace(
            workspace_id=workspace_id,
            market=(market or "").strip().upper() or None,
            limit=cap,
        )
    except Exception as e:
        logger.warning("category_discovery failed workspace_id=%s: %s", workspace_id, e)
        return empty_category_result()
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


def get_discovery_summary(workspace_id: int) -> Dict[str, Any]:
    """Return discovery summary counts for workspace. Safe empty state."""
    try:
        kw = list_keyword_discovery_for_workspace(workspace_id, limit=10000)
        mk = list_market_discovery_for_workspace(workspace_id, limit=100)
        cat = list_category_discovery_for_workspace(workspace_id, limit=10000)
        return discovery_summary_shape(
            workspace_id=workspace_id,
            keyword_count=len(kw),
            market_count=len(mk),
            category_count=len(cat),
        )
    except Exception as e:
        logger.warning("discovery_summary failed workspace_id=%s: %s", workspace_id, e)
        return discovery_summary_shape(workspace_id=workspace_id)
