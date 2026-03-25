"""
Step 238: Real market/keyword discovery API routes. Workspace-scoped; reuses discovery_api service.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from amazon_research.logging_config import get_logger

logger = get_logger("api_gateway.discovery")

router = APIRouter()


def _get_workspace_or_raise(workspace_id: int) -> None:
    """Raise 403 if workspace does not exist. Step 200 isolation."""
    from amazon_research.db import get_workspace
    if get_workspace(workspace_id) is None:
        raise HTTPException(status_code=403, detail="invalid workspace_id")


@router.get("/keywords")
def get_discovery_keywords(
    workspace_id: int = Path(..., description="Workspace ID"),
    q: Optional[str] = Query(None, max_length=100, description="Keyword text filter"),
    market: Optional[str] = Query(None, max_length=10, description="Market filter (DE, US, AU)"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    sort: str = Query("recent", description="Sort: recent, keyword, market"),
) -> Dict[str, Any]:
    """Step 238: Keyword discovery for workspace. Real data from keyword_seeds; safe empty state."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.discovery_api import get_keyword_discovery
        return get_keyword_discovery(workspace_id=workspace_id, q=q, market=market, limit=limit, sort=sort)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("discovery keywords failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        from amazon_research.discovery_api.discovery_types import empty_keyword_result
        return empty_keyword_result()


@router.get("/markets")
def get_discovery_markets(
    workspace_id: int = Path(..., description="Workspace ID"),
    category: Optional[str] = Query(None, max_length=100, description="Category filter"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
) -> Dict[str, Any]:
    """Step 238: Market discovery for workspace. Real data from seeds and opportunity_memory; safe empty state."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.discovery_api import get_market_discovery
        return get_market_discovery(workspace_id=workspace_id, category=category, limit=limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("discovery markets failed workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        from amazon_research.discovery_api.discovery_types import empty_market_result
        return empty_market_result()


@router.get("/clusters")
def get_discovery_clusters(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Steps 243–245: Keyword opportunity clusters. Deterministic, workspace-scoped."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.research_intelligence import get_clusters
        items = get_clusters(workspace_id)
    except Exception as e:
        logger.warning("discovery clusters failed workspace_id=%s: %s", workspace_id, e)
        return {"data": [], "meta": {"workspace_id": workspace_id, "count": 0}}
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


@router.get("/category-explorer")
def get_discovery_category_explorer(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Steps 243–245: Category opportunity explorer. Workspace-scoped."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.research_intelligence import get_category_explorer
        items = get_category_explorer(workspace_id)
    except Exception as e:
        logger.warning("category explorer failed workspace_id=%s: %s", workspace_id, e)
        return {"data": [], "meta": {"workspace_id": workspace_id, "count": 0}}
    return {"data": items, "meta": {"workspace_id": workspace_id, "count": len(items)}}


@router.get("/categories")
def get_discovery_categories(
    workspace_id: int = Path(..., description="Workspace ID"),
    market: Optional[str] = Query(None, max_length=10),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """Step 238 (optional): Category discovery for workspace. Safe empty state."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.discovery_api.discovery_service import get_category_discovery
        return get_category_discovery(workspace_id=workspace_id, market=market, limit=limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("discovery categories failed workspace_id=%s: %s", workspace_id, e)
        from amazon_research.discovery_api.discovery_types import empty_category_result
        return empty_category_result()


@router.get("/summary")
def get_discovery_summary_route(
    workspace_id: int = Path(..., description="Workspace ID"),
) -> Dict[str, Any]:
    """Step 238 (optional): Discovery summary counts for workspace."""
    _get_workspace_or_raise(workspace_id)
    try:
        from amazon_research.discovery_api.discovery_service import get_discovery_summary
        return get_discovery_summary(workspace_id=workspace_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("discovery summary failed workspace_id=%s: %s", workspace_id, e)
        from amazon_research.discovery_api.discovery_types import discovery_summary
        return discovery_summary(workspace_id=workspace_id)
