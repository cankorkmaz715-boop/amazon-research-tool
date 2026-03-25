"""
Step 234: Real opportunity feed service – single entry for dashboard and API.
Step 235: Uses calibrated ranking (scoring/ranking calibration) for sorted, scored feed.
Step 236: Prefers persisted current feed when available; persists after compute.
"""
from typing import Any, Dict, List, Optional, Tuple

from amazon_research.logging_config import get_logger

from amazon_research.opportunity_feed.opportunity_feed_repository import (
    DEFAULT_FEED_LIMIT,
    list_real_opportunities_for_workspace,
)
from amazon_research.opportunity_feed.opportunity_feed_mapper import map_to_feed_items
from amazon_research.opportunity_feed.opportunity_feed_types import SOURCE_REAL

logger = get_logger("opportunity_feed.service")


def get_real_opportunity_feed(
    workspace_id: Optional[int],
    limit: int = DEFAULT_FEED_LIMIT,
    prefer_persisted: bool = True,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Return (feed_items, is_real).
    - Step 236: When prefer_persisted and persisted current has items, return those.
    - Else: feed from opportunity_memory + rankings, calibrated; then persist snapshot and return.
    - When none: feed_items=[], is_real=True (demo fallback safe). Never raises.
    """
    if workspace_id is None:
        logger.debug("opportunity_feed get_real_opportunity_feed skipped workspace_id=None")
        return [], True
    try:
        # Step 236: prefer persisted current feed when available
        if prefer_persisted:
            try:
                from amazon_research.opportunity_persistence import get_feed_from_persistence
                persisted = get_feed_from_persistence(workspace_id, limit=limit)
                if persisted:
                    logger.info(
                        "opportunity_feed served from persistence workspace_id=%s count=%s",
                        workspace_id,
                        len(persisted),
                        extra={"workspace_id": workspace_id, "count": len(persisted)},
                    )
                    return persisted[:limit], True
            except Exception as pe:
                logger.debug("opportunity_feed persisted read skipped workspace_id=%s: %s", workspace_id, pe)
        # Compute from pipeline (calibrated)
        try:
            from amazon_research.opportunity_scoring import get_calibrated_opportunity_rows
            rows = get_calibrated_opportunity_rows(workspace_id, limit=limit)
        except Exception as cal_e:
            logger.warning("opportunity_feed calibration fallback workspace_id=%s: %s", workspace_id, cal_e)
            rows = list_real_opportunities_for_workspace(workspace_id, limit=limit)
        if not rows:
            logger.info(
                "opportunity_feed real feed empty workspace_id=%s (demo fallback safe)",
                workspace_id,
                extra={"workspace_id": workspace_id},
            )
            return [], True
        items = map_to_feed_items(rows, source_type=SOURCE_REAL)
        # Step 236: persist snapshot (best-effort; do not block)
        try:
            from amazon_research.opportunity_persistence import persist_feed_snapshot
            persist_feed_snapshot(workspace_id, items, write_history=True)
        except Exception as pe:
            logger.debug("opportunity_feed persist snapshot skipped workspace_id=%s: %s", workspace_id, pe)
        logger.info(
            "opportunity_feed real feed loaded workspace_id=%s count=%s",
            workspace_id,
            len(items),
            extra={"workspace_id": workspace_id, "count": len(items)},
        )
        return items, True
    except Exception as e:
        logger.warning(
            "opportunity_feed real feed load failed workspace_id=%s: %s",
            workspace_id,
            e,
            extra={"workspace_id": workspace_id},
        )
        return [], True


def get_opportunity_feed_for_dashboard(
    workspace_id: Optional[int],
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Return feed items for dashboard top_opportunities slot.
    Real data when available; otherwise empty list (dashboard/demo layer will substitute demo when appropriate).
    """
    items, _ = get_real_opportunity_feed(workspace_id, limit=limit)
    return items
