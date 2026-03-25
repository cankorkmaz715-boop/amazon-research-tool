"""
Step 237: Live opportunity stream service – entry for scheduler/runtime.
Runs feed refresh cycle; logs start/end and counts. Does not block request handlers.
"""
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

from amazon_research.opportunity_stream.opportunity_refresh_runner import run_feed_refresh_cycle

logger = get_logger("opportunity_stream.service")


def run_live_feed_refresh_cycle() -> Dict[str, Any]:
    """
    Run one live feed refresh cycle: refresh persisted opportunity feed for all workspaces.
    Reuses real feed + scoring + persistence. Safe no-op when no workspaces; failures isolated.
    Returns summary dict. Never raises.
    """
    logger.info("opportunity_stream live refresh cycle start", extra={"service": "opportunity_stream"})
    try:
        results = run_feed_refresh_cycle()
        total = len(results)
        updated = sum(1 for r in results if (r.get("opportunity_count") or 0) > 0)
        errors = sum(1 for r in results if r.get("error"))
        logger.info(
            "opportunity_stream live refresh cycle end workspaces=%s updated=%s errors=%s",
            total,
            updated,
            errors,
            extra={"workspaces": total, "updated": updated, "errors": errors},
        )
        return {
            "workspaces_processed": total,
            "workspaces_with_opportunities": updated,
            "workspaces_with_errors": errors,
            "results": results,
        }
    except Exception as e:
        logger.warning("opportunity_stream live refresh cycle failed: %s", e, exc_info=True)
        return {
            "workspaces_processed": 0,
            "workspaces_with_opportunities": 0,
            "workspaces_with_errors": 1,
            "results": [],
            "cycle_error": str(e),
        }
