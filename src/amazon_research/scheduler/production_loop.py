"""
Step 183: Scheduler production loop – continuous research cycles for production.
Coordinates: discovery, refresh, signal update, opportunity scoring, anomaly monitoring.
Controlled intervals, no overlapping jobs, cycle start/complete/duration/error logging.
Lightweight and safe for long-running operation. Compatible with runtime service and worker queue.
"""
import time
from typing import Any, Callable, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("scheduler.production_loop")

# Cycle names
CYCLE_DISCOVERY = "discovery"
CYCLE_REFRESH = "refresh"
CYCLE_SIGNAL_UPDATE = "signal_update"
CYCLE_OPPORTUNITY_SCORING = "opportunity_scoring"
CYCLE_ANOMALY_MONITORING = "anomaly_monitoring"
CYCLE_WORKSPACE_INTELLIGENCE_REFRESH = "workspace_intelligence_refresh"
CYCLE_OPPORTUNITY_FEED_REFRESH = "opportunity_feed_refresh"  # Step 237

# Default intervals (seconds)
DEFAULT_INTERVALS: Dict[str, float] = {
    CYCLE_DISCOVERY: 1800.0,           # 30 min
    CYCLE_REFRESH: 900.0,              # 15 min
    CYCLE_SIGNAL_UPDATE: 600.0,        # 10 min
    CYCLE_OPPORTUNITY_SCORING: 1200.0,  # 20 min
    CYCLE_ANOMALY_MONITORING: 300.0,   # 5 min
    CYCLE_WORKSPACE_INTELLIGENCE_REFRESH: 3600.0,  # 60 min; override via WORKSPACE_INTELLIGENCE_REFRESH_INTERVAL_MINUTES
    CYCLE_OPPORTUNITY_FEED_REFRESH: 1800.0,        # Step 237: 30 min
}

# In-memory state: last run time and running flag per cycle
_cycle_last_run: Dict[str, float] = {}
_cycle_running: Dict[str, bool] = {c: False for c in DEFAULT_INTERVALS}


def _run_discovery_cycle() -> None:
    try:
        from amazon_research.scheduler import get_runner
        get_runner().run_once(CYCLE_DISCOVERY)
    except Exception as e:
        raise RuntimeError(f"discovery cycle failed: {e}") from e


def _run_refresh_cycle() -> None:
    try:
        from amazon_research.scheduler import get_runner
        get_runner().run_once(CYCLE_REFRESH)
    except Exception as e:
        raise RuntimeError(f"refresh cycle failed: {e}") from e


def _run_signal_update_cycle() -> None:
    try:
        from amazon_research.monitoring.signal_drift_detector import run_drift_checks
        run_drift_checks(current_context=None, history_contexts=None, target_id="production_loop")
    except Exception as e:
        raise RuntimeError(f"signal update cycle failed: {e}") from e


def _run_opportunity_scoring_cycle() -> None:
    try:
        from amazon_research.scheduler import get_runner
        get_runner().run_once("scoring")
    except Exception as e:
        raise RuntimeError(f"opportunity scoring cycle failed: {e}") from e


def _run_anomaly_monitoring_cycle() -> None:
    try:
        from amazon_research.discovery.anomaly_alert_engine import get_anomaly_alerts
        get_anomaly_alerts(target_entity="", drift_reports=None, lifecycle_output=None)
    except Exception as e:
        raise RuntimeError(f"anomaly monitoring cycle failed: {e}") from e


def _run_workspace_intelligence_refresh_cycle() -> None:
    """Step 193: Refresh workspace intelligence snapshots for stale workspaces (batch, per-workspace isolation)."""
    try:
        from amazon_research.workspace_intelligence.scheduler import run_workspace_intelligence_refresh_cycle
        run_workspace_intelligence_refresh_cycle()
    except Exception as e:
        raise RuntimeError(f"workspace_intelligence refresh cycle failed: {e}") from e


def _run_opportunity_feed_refresh_cycle() -> None:
    """Step 237: Live opportunity stream – refresh persisted feed from pipeline for all workspaces."""
    try:
        from amazon_research.opportunity_stream import run_live_feed_refresh_cycle
        run_live_feed_refresh_cycle()
    except Exception as e:
        raise RuntimeError(f"opportunity_feed refresh cycle failed: {e}") from e


_CYCLE_RUNNERS: Dict[str, Callable[[], None]] = {
    CYCLE_DISCOVERY: _run_discovery_cycle,
    CYCLE_REFRESH: _run_refresh_cycle,
    CYCLE_SIGNAL_UPDATE: _run_signal_update_cycle,
    CYCLE_OPPORTUNITY_SCORING: _run_opportunity_scoring_cycle,
    CYCLE_ANOMALY_MONITORING: _run_anomaly_monitoring_cycle,
    CYCLE_WORKSPACE_INTELLIGENCE_REFRESH: _run_workspace_intelligence_refresh_cycle,
    CYCLE_OPPORTUNITY_FEED_REFRESH: _run_opportunity_feed_refresh_cycle,
}


def _run_one_cycle(cycle_name: str, now: float) -> Optional[Dict[str, Any]]:
    """Run a single cycle if not already running. Returns result dict or None if skipped."""
    global _cycle_running, _cycle_last_run
    if _cycle_running.get(cycle_name):
        return None
    interval = DEFAULT_INTERVALS.get(cycle_name, 300.0)
    last = _cycle_last_run.get(cycle_name, 0.0)
    if now - last < interval:
        return None
    runner = _CYCLE_RUNNERS.get(cycle_name)
    if not runner:
        return None
    _cycle_running[cycle_name] = True
    start = time.time()
    result: Dict[str, Any] = {
        "cycle": cycle_name,
        "started_at": now,
        "duration_seconds": None,
        "error": None,
        "completed": False,
    }
    try:
        logger.info("production cycle start", extra={"cycle": cycle_name})
        runner()
        result["duration_seconds"] = round(time.time() - start, 2)
        result["completed"] = True
        _cycle_last_run[cycle_name] = time.time()
        logger.info(
            "production cycle completion",
            extra={"cycle": cycle_name, "duration_seconds": result["duration_seconds"]},
        )
    except Exception as e:
        result["duration_seconds"] = round(time.time() - start, 2)
        result["error"] = str(e)
        result["completed"] = False
        logger.error(
            "production cycle error",
            extra={"cycle": cycle_name, "error": str(e), "duration_seconds": result["duration_seconds"]},
            exc_info=True,
        )
    finally:
        _cycle_running[cycle_name] = False
    return result


def run_production_scheduler_tick(
    now: Optional[float] = None,
    intervals: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Run all due production cycles (one at a time, no overlap). Uses in-memory last-run and running flags.
    Returns summary: cycles_run (list of result dicts), cycles_skipped (list of names), any_errors (bool).
    """
    t = now if now is not None else time.time()
    intervals = intervals or DEFAULT_INTERVALS
    cycles_run: list = []
    cycles_skipped: list = []
    for cycle_name in [CYCLE_DISCOVERY, CYCLE_REFRESH, CYCLE_SIGNAL_UPDATE, CYCLE_OPPORTUNITY_SCORING, CYCLE_ANOMALY_MONITORING, CYCLE_WORKSPACE_INTELLIGENCE_REFRESH, CYCLE_OPPORTUNITY_FEED_REFRESH]:
        interval = intervals.get(cycle_name, DEFAULT_INTERVALS.get(cycle_name, 300.0))
        if cycle_name == CYCLE_WORKSPACE_INTELLIGENCE_REFRESH:
            try:
                from amazon_research.workspace_intelligence.refresh_policy import get_refresh_interval_minutes
                interval = max(60.0, get_refresh_interval_minutes() * 60.0)
                DEFAULT_INTERVALS[cycle_name] = interval
            except Exception:
                pass
        last = _cycle_last_run.get(cycle_name, 0.0)
        if _cycle_running.get(cycle_name):
            cycles_skipped.append(cycle_name)
            continue
        if t - last < interval:
            continue
        res = _run_one_cycle(cycle_name, t)
        if res:
            cycles_run.append(res)
        else:
            cycles_skipped.append(cycle_name)
    any_errors = any(r.get("error") for r in cycles_run)
    return {
        "cycles_run": cycles_run,
        "cycles_skipped": cycles_skipped,
        "any_errors": any_errors,
        "tick_at": t,
    }


def get_production_loop_status() -> Dict[str, Any]:
    """Return current state for host-side checks: last run times and running flags."""
    return {
        "cycle_last_run": dict(_cycle_last_run),
        "cycle_running": dict(_cycle_running),
        "intervals": dict(DEFAULT_INTERVALS),
    }


def set_cycle_interval(cycle_name: str, interval_seconds: float) -> None:
    """Override interval for a cycle (e.g. for tests)."""
    if cycle_name in DEFAULT_INTERVALS:
        DEFAULT_INTERVALS[cycle_name] = max(1.0, interval_seconds)
