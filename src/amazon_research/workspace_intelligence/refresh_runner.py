"""
Step 193: Workspace intelligence refresh runner – run refresh for a batch of workspaces.
Isolates failures per workspace; never crashes; logs start/success/failure per workspace.
"""
import time
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("workspace_intelligence.refresh_runner")


def run_refresh_for_workspaces(workspace_ids: List[int]) -> Dict[str, Any]:
    """
    Trigger refresh_workspace_intelligence_summary for each workspace_id.
    Persistence is done inside refresh (Step 192). Returns stats: refreshed, failed, results.
    Failures are logged; processing continues for other workspaces.
    """
    refreshed: List[int] = []
    failed: List[Dict[str, Any]] = []
    results: Dict[int, Dict[str, Any]] = {}

    for wid in workspace_ids or []:
        start = time.time()
        try:
            from amazon_research.workspace_isolation import require_workspace_context
            if require_workspace_context(wid, "scheduler_refresh"):
                logger.info(
                    "workspace_intelligence scheduler workspace scope enforcement workspace_id=%s",
                    wid,
                    extra={"workspace_id": wid},
                )
        except Exception:
            pass
        try:
            from amazon_research.workspace_intelligence.metrics import record_refresh_attempt, record_refresh_success, record_refresh_failure
            record_refresh_attempt()
        except Exception:
            pass
        logger.info(
            "workspace_intelligence refresh start workspace_id=%s",
            wid,
            extra={"workspace_id": wid},
        )
        try:
            from amazon_research.worker_stability import execute_with_stability
            from amazon_research.workspace_intelligence import refresh_workspace_intelligence_summary
            from amazon_research.error_recovery import run_with_failsafe

            def _do_refresh():
                return refresh_workspace_intelligence_summary(wid)

            def _run():
                return execute_with_stability(
                    _do_refresh,
                    workspace_id=wid,
                    job_type="intelligence_refresh",
                    use_lock=True,
                    use_timeout=True,
                    use_retry=True,
                )

            def _get_cached():
                try:
                    from amazon_research.workspace_intelligence import get_workspace_intelligence_summary_prefer_cached
                    summary = get_workspace_intelligence_summary_prefer_cached(wid)
                    if summary is not None and isinstance(summary, dict):
                        return {"ok": True, "result": summary, "from_fallback": "cached"}
                except Exception:
                    pass
                return None

            stability_result = run_with_failsafe(
                _run,
                workspace_id=wid,
                path_key="intelligence_refresh",
                get_cached=_get_cached,
            )
            duration = round(time.time() - start, 2)
            if stability_result.get("skipped"):
                results[wid] = {"ok": False, "skipped": True, "reason": stability_result.get("error", "locked"), "duration_seconds": duration}
                logger.info(
                    "workspace_intelligence refresh skipped (stability) workspace_id=%s reason=%s",
                    wid, stability_result.get("error"),
                    extra={"workspace_id": wid},
                )
            elif stability_result.get("ok"):
                refreshed.append(wid)
                results[wid] = {"ok": True, "duration_seconds": duration}
                try:
                    record_refresh_success(duration_seconds=duration)
                except Exception:
                    pass
                logger.info(
                    "workspace_intelligence refresh success workspace_id=%s duration_seconds=%s",
                    wid,
                    duration,
                    extra={"workspace_id": wid, "duration_seconds": duration},
                )
                try:
                    from amazon_research.workspace_activity_log import create_workspace_activity_event
                    create_workspace_activity_event(wid, "intelligence_refresh", source_module="workspace_intelligence", event_payload={"duration_seconds": duration})
                except Exception:
                    pass
            else:
                err = stability_result.get("error", "unknown")
                failed.append({"workspace_id": wid, "error": err})
                results[wid] = {"ok": False, "error": err, "duration_seconds": duration}
                try:
                    record_refresh_failure(duration_seconds=duration)
                except Exception:
                    pass
                logger.warning(
                    "workspace_intelligence refresh failure workspace_id=%s error=%s",
                    wid,
                    err,
                    extra={"workspace_id": wid, "error": err, "duration_seconds": duration},
                )
        except Exception as e:
            duration = round(time.time() - start, 2)
            failed.append({"workspace_id": wid, "error": str(e)})
            results[wid] = {"ok": False, "error": str(e), "duration_seconds": duration}
            try:
                record_refresh_failure(duration_seconds=duration)
            except Exception:
                pass
            logger.warning(
                "workspace_intelligence refresh failure workspace_id=%s error=%s",
                wid,
                e,
                extra={"workspace_id": wid, "error": str(e), "duration_seconds": duration},
            )
    return {
        "refreshed": refreshed,
        "failed": failed,
        "results": results,
        "refreshed_count": len(refreshed),
        "failed_count": len(failed),
    }
