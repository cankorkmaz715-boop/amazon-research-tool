"""
Scheduler runner – run discovery, refresh, scoring once or by name. Ready for cron/queue later.
Step 23: one-run pipeline (discovery → refresh → scoring); fail gracefully and report where stopped.
"""
from typing import Any, Callable, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("scheduler")

# Fixed pipeline order for run_pipeline()
PIPELINE_ORDER = ["discovery", "refresh", "scoring"]


class SchedulerRunner:
    """
    Register tasks (name, callable, kwargs). run_once() runs one or all; run_pipeline() runs in fixed sequence.
    """

    def __init__(self) -> None:
        self._tasks: List[tuple] = []  # (name, fn, kwargs)
        self._by_name: Dict[str, tuple] = {}

    def register(self, name: str, fn: Callable[..., Any], **kwargs: Any) -> None:
        """Register a task: run with fn(**kwargs) when name is used."""
        entry = (name, fn, kwargs)
        self._tasks.append(entry)
        self._by_name[name] = entry
        logger.info("scheduler registered task", extra={"task": name})

    def run_once(self, task_name: Optional[str] = None) -> List[str]:
        """
        Run one task by name, or all if task_name is None.
        Returns list of task names that were run (for logging). Exceptions are logged, not raised.
        """
        if task_name:
            for name, fn, opts in self._tasks:
                if name == task_name:
                    try:
                        fn(**opts)
                        return [name]
                    except Exception as e:
                        logger.exception("scheduler task failed: %s", name, extra={"error": str(e)})
                        return []
            logger.warning("scheduler task not found", extra={"task": task_name})
            return []
        ran = []
        for name, fn, opts in self._tasks:
            try:
                fn(**opts)
                ran.append(name)
            except Exception as e:
                logger.exception("scheduler task failed: %s", name, extra={"error": str(e)})
        return ran

    def run_pipeline(self) -> Dict[str, Any]:
        """
        Run discovery → refresh → scoring in sequence (one-run, no daemon).
        If a stage fails, log and return immediately with ok=False and stopped_at=stage name.
        Returns dict: ok (bool), stages_completed (list), stopped_at (str or None), error (str or None).
        """
        result: Dict[str, Any] = {
            "ok": False,
            "stages_completed": [],
            "stopped_at": None,
            "error": None,
        }
        for name in PIPELINE_ORDER:
            entry = self._by_name.get(name)
            if not entry:
                logger.warning("pipeline stage not registered: %s", name)
                result["stopped_at"] = name
                result["error"] = "stage not registered"
                return result
            _, fn, opts = entry
            try:
                logger.info("scheduler pipeline stage starting", extra={"stage": name})
                fn(**opts)
                result["stages_completed"].append(name)
                try:
                    from amazon_research.db import record_usage
                    record_usage(None, f"{name}_run")
                except Exception:
                    pass
                logger.info("scheduler pipeline stage finished", extra={"stage": name})
            except Exception as e:
                logger.exception("scheduler pipeline stage failed: %s", name, extra={"error": str(e)})
                result["stopped_at"] = name
                result["error"] = str(e)
                try:
                    from amazon_research.monitoring import send_pipeline_failure_alert
                    send_pipeline_failure_alert(result)
                except Exception:
                    pass
                return result
        result["ok"] = True
        return result


def get_runner() -> SchedulerRunner:
    """Return a runner with discovery, refresh, scoring tasks registered. Limits from config tuning."""
    from amazon_research.bots import AsinDiscoveryBot, DataRefreshBot, ScoringEngine
    from amazon_research.config import get_config
    runner = SchedulerRunner()
    runner.register("discovery", lambda: AsinDiscoveryBot().run())
    runner.register(
        "refresh",
        lambda: DataRefreshBot().run(limit=get_config().scheduler_refresh_limit),
    )
    runner.register(
        "scoring",
        lambda: ScoringEngine().run(limit=get_config().scheduler_scoring_limit),
    )
    return runner
