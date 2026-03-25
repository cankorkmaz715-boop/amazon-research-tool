"""
Step 235: Scoring service – calibrated opportunity rows for feed/dashboard.
Uses existing opportunity_feed repository + calibrator; no second ranking engine.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from amazon_research.opportunity_scoring.opportunity_ranking_calibrator import calibrate_opportunity_rows

logger = get_logger("opportunity_scoring.service")


def get_calibrated_opportunity_rows(
    workspace_id: Optional[int],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Return workspace-scoped opportunity rows sorted and calibrated (normalized_score,
    ranking_position, priority_band, supporting_signal_hints). Uses existing
    opportunity_memory + opportunity_rankings via opportunity_feed repository.
    Safe empty list when no data or on error; partial signals get safe defaults.
    """
    if workspace_id is None:
        logger.debug("opportunity_scoring get_calibrated_opportunity_rows skipped workspace_id=None")
        return []
    try:
        from amazon_research.opportunity_feed.opportunity_feed_repository import list_real_opportunities_for_workspace
        rows = list_real_opportunities_for_workspace(workspace_id, limit=limit)
        if not rows:
            logger.info(
                "opportunity_scoring calibrated feed empty workspace_id=%s",
                workspace_id,
                extra={"workspace_id": workspace_id},
            )
            return []
        calibrated = calibrate_opportunity_rows(rows, workspace_id=workspace_id)
        logger.info(
            "opportunity_scoring calibrated workspace_id=%s count=%s",
            workspace_id,
            len(calibrated),
            extra={"workspace_id": workspace_id, "count": len(calibrated)},
        )
        return calibrated
    except Exception as e:
        logger.warning(
            "opportunity_scoring get_calibrated_opportunity_rows failed workspace_id=%s: %s",
            workspace_id,
            e,
            extra={"workspace_id": workspace_id},
        )
        return []
