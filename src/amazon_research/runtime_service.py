"""
Step 181: Runtime service entrypoint – long-lived process for the Amazon research platform.
Initializes and coordinates: scheduler, worker queue/worker loop, telemetry/monitoring, discovery orchestration (where safe).
Deterministic startup, graceful shutdown (SIGINT/SIGTERM), conservative loop. Suitable for systemd.
"""
import signal
import time
from typing import Any, Dict, Optional

# Shutdown flag; set by signal handler
_shutdown_requested = False
_worker_cycles = 0
_last_worker_summary: Optional[Dict[str, Any]] = None


def _handle_shutdown(signum: int, frame: Any) -> None:
    global _shutdown_requested
    _shutdown_requested = True


def get_runtime_status() -> Dict[str, Any]:
    """Expose clear runtime status for host-side testing and monitoring."""
    return {
        "running": not _shutdown_requested,
        "worker_cycles": _worker_cycles,
        "last_worker_summary": _last_worker_summary,
        "shutdown_requested": _shutdown_requested,
    }


def init_runtime() -> Dict[str, Any]:
    """
    Initialize runtime: config, logging, DB, optional Sentry. Deterministic and safe.
    Returns status dict with keys: ok, message, stages.
    """
    from amazon_research.logging_config import setup_logging, get_logger
    log = None
    stages = []
    try:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            stages.append("dotenv")
        except Exception:
            stages.append("dotenv_skip")
        setup_logging()
        log = get_logger("runtime_service")
        stages.append("logging")
        try:
            from amazon_research.monitoring import init_sentry
            init_sentry()
            stages.append("sentry")
        except Exception:
            stages.append("sentry_skip")
        from amazon_research.db import init_db
        init_db()
        stages.append("db")
        if log:
            log.info("runtime init complete", extra={"stages": stages})
        return {"ok": True, "message": "init complete", "stages": stages}
    except Exception as e:
        if log:
            log.exception("runtime init failed")
        return {"ok": False, "message": str(e), "stages": stages}


def run_runtime_service(
    worker_interval_seconds: float = 60.0,
    worker_max_jobs_per_cycle: int = 50,
    pipeline_interval_seconds: float = 0.0,
    shutdown_timeout_seconds: float = 30.0,
) -> Dict[str, Any]:
    """
    Run the long-lived runtime loop: worker cycles + optional pipeline on interval.
    Respects SIGINT/SIGTERM for graceful shutdown. Returns final status dict.
    """
    global _shutdown_requested, _worker_cycles, _last_worker_summary
    from amazon_research.logging_config import get_logger
    log = get_logger("runtime_service")

    # Register signal handlers
    try:
        signal.signal(signal.SIGINT, _handle_shutdown)
        signal.signal(signal.SIGTERM, _handle_shutdown)
    except Exception as e:
        log.warning("signal registration failed: %s", e)

    log.info("runtime service starting", extra={
        "worker_interval_seconds": worker_interval_seconds,
        "worker_max_jobs_per_cycle": worker_max_jobs_per_cycle,
        "pipeline_interval_seconds": pipeline_interval_seconds,
    })

    pipeline_interval_seconds = max(0.0, pipeline_interval_seconds)
    last_pipeline_run = 0.0
    _worker_cycles = 0
    _shutdown_requested = False

    while not _shutdown_requested:
        # Worker loop (process queued jobs)
        try:
            from amazon_research.scheduler import run_worker_loop
            summary = run_worker_loop(max_jobs=worker_max_jobs_per_cycle)
            _last_worker_summary = summary
            _worker_cycles += 1
            if summary.get("jobs_processed", 0) > 0:
                log.info("worker cycle done", extra=summary)
        except Exception as e:
            log.exception("worker cycle failed: %s", e)

        # Optional: run discovery pipeline on interval (only where safe and already implemented)
        if pipeline_interval_seconds > 0:
            now = time.time()
            if now - last_pipeline_run >= pipeline_interval_seconds:
                try:
                    from amazon_research.scheduler import get_runner
                    runner = get_runner()
                    result = runner.run_pipeline()
                    last_pipeline_run = now
                    if result.get("ok"):
                        log.info("pipeline run done", extra={"stages": result.get("stages_completed", [])})
                    else:
                        log.warning("pipeline run stopped", extra=result)
                except Exception as e:
                    log.exception("pipeline run failed: %s", e)

        # Sleep until next cycle or shutdown
        slept = 0.0
        while slept < worker_interval_seconds and not _shutdown_requested:
            time.sleep(min(1.0, worker_interval_seconds - slept))
            slept += 1.0

    log.info("runtime service shutdown requested; exiting gracefully")
    return get_runtime_status()


def main() -> None:
    """CLI entrypoint: init then run runtime service until shutdown."""
    status = init_runtime()
    if not status.get("ok"):
        raise SystemExit(1)
    run_runtime_service(
        worker_interval_seconds=60.0,
        worker_max_jobs_per_cycle=50,
        pipeline_interval_seconds=0.0,
    )


if __name__ == "__main__":
    main()
