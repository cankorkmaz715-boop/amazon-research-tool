"""
Step 237: Runtime feed refresh runner – compute feed from pipeline and persist for each workspace.
Reuses real opportunity feed + scoring + persistence; no second pipeline.
Safe no-op when no new data; per-workspace isolation; failures do not crash cycle.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from amazon_research.opportunity_stream.opportunity_stream_types import (
    MAX_WORKSPACES_PER_REFRESH,
    refresh_result,
)

logger = get_logger("opportunity_stream.refresh_runner")


def run_feed_refresh_for_workspace(workspace_id: int, limit: int = 100) -> Dict[str, Any]:
    """
    Refresh persisted feed for one workspace: compute from pipeline (prefer_persisted=False)
    so we always recompute and persist. Returns refresh_result dict. Never raises.
    """
    if workspace_id is None:
        return refresh_result(0, 0, error="workspace_id required")
    try:
        from amazon_research.opportunity_feed.opportunity_feed_service import get_real_opportunity_feed
        # Force compute + persist (do not prefer persisted) so runtime refresh updates state
        items, _ = get_real_opportunity_feed(workspace_id, limit=limit, prefer_persisted=False)
        count = len(items) if items else 0
        logger.info(
            "opportunity_stream refresh workspace_id=%s count=%s",
            workspace_id,
            count,
            extra={"workspace_id": workspace_id, "count": count},
        )
        return refresh_result(workspace_id, count, error=None)
    except Exception as e:
        logger.warning(
            "opportunity_stream refresh failed workspace_id=%s: %s",
            workspace_id,
            e,
            extra={"workspace_id": workspace_id},
        )
        return refresh_result(workspace_id, 0, error=str(e))


def run_feed_refresh_cycle() -> List[Dict[str, Any]]:
    """
    Run feed refresh for all workspaces (up to MAX_WORKSPACES_PER_REFRESH).
    Returns list of refresh_result dicts. Never raises; per-workspace failure isolated.
    """
    try:
        from amazon_research.db import list_workspaces
        workspaces = list_workspaces() or []
    except Exception as e:
        logger.warning("opportunity_stream refresh cycle list_workspaces failed: %s", e)
        return []
    ids = []
    for w in workspaces[:MAX_WORKSPACES_PER_REFRESH]:
        wid = w.get("id") if isinstance(w, dict) else None
        if wid is not None:
            ids.append(int(wid))
    if not ids:
        logger.debug("opportunity_stream refresh cycle no workspaces")
        return []
    results: List[Dict[str, Any]] = []
    for workspace_id in ids:
        try:
            res = run_feed_refresh_for_workspace(workspace_id)
            results.append(res)
        except Exception as e:
            logger.warning("opportunity_stream refresh cycle workspace_id=%s: %s", workspace_id, e)
            results.append(refresh_result(workspace_id, 0, error=str(e)))
    return results
