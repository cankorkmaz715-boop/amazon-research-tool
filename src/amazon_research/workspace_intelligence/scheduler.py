"""
Step 193: Workspace intelligence refresh scheduler – one cycle to refresh stale workspace snapshots.
Integrates with production loop; does not start a separate long-running scheduler.
"""
import time
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .refresh_policy import get_refresh_batch, workspaces_requiring_refresh
from .refresh_runner import run_refresh_for_workspaces

logger = get_logger("workspace_intelligence.scheduler")


def run_workspace_intelligence_refresh_cycle(
    batch_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run one workspace intelligence refresh cycle: select workspaces needing refresh,
    run refresh (compute + persist) for each in batch. Never raises; logs and returns stats.
    """
    cycle_start = time.time()
    logger.info(
        "workspace_intelligence scheduler cycle start",
        extra={"cycle_start": cycle_start},
    )
    result: Dict[str, Any] = {
        "cycle_start": cycle_start,
        "candidates": [],
        "refreshed": [],
        "failed": [],
        "refreshed_count": 0,
        "failed_count": 0,
        "duration_seconds": None,
        "error": None,
    }
    try:
        candidates: List[int] = workspaces_requiring_refresh(batch_limit=batch_limit)
        result["candidates"] = candidates
        if not candidates:
            result["duration_seconds"] = round(time.time() - cycle_start, 2)
            logger.info(
                "workspace_intelligence scheduler cycle complete no_candidates duration_seconds=%s",
                result["duration_seconds"],
                extra=result,
            )
            return result
        run_result = run_refresh_for_workspaces(candidates)
        result["refreshed"] = run_result.get("refreshed") or []
        result["failed"] = run_result.get("failed") or []
        result["refreshed_count"] = run_result.get("refreshed_count", 0)
        result["failed_count"] = run_result.get("failed_count", 0)
        result["results"] = run_result.get("results") or {}
        result["duration_seconds"] = round(time.time() - cycle_start, 2)
        logger.info(
            "workspace_intelligence scheduler cycle complete refreshed=%s failed=%s duration_seconds=%s",
            result["refreshed_count"],
            result["failed_count"],
            result["duration_seconds"],
            extra=result,
        )
        return result
    except Exception as e:
        result["duration_seconds"] = round(time.time() - cycle_start, 2)
        result["error"] = str(e)
        logger.warning(
            "workspace_intelligence scheduler cycle error error=%s duration_seconds=%s",
            e,
            result["duration_seconds"],
            extra=result,
        )
        return result
