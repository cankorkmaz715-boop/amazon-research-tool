#!/usr/bin/env python3
"""Step 181: Runtime service entrypoint – startup init, worker, scheduler, graceful shutdown."""
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    startup_ok = False
    worker_ok = False
    scheduler_ok = False
    shutdown_ok = False

    # 1) Startup init: init_runtime() runs and returns status with stages (ok or partial when DB unavailable)
    try:
        from amazon_research.runtime_service import init_runtime, get_runtime_status
        status = init_runtime()
        stages = status.get("stages") or []
        startup_ok = isinstance(status, dict) and "stages" in status and (
            status.get("ok") is True or "logging" in stages
        )
    except Exception as e:
        print(f"startup init FAIL: {e}")
        startup_ok = False

    # 2) Worker startup: run_worker_loop(max_jobs=0) returns summary dict
    try:
        from amazon_research.scheduler import run_worker_loop
        summary = run_worker_loop(max_jobs=0)
        worker_ok = isinstance(summary, dict) and "jobs_processed" in summary
    except Exception as e:
        print(f"worker startup FAIL: {e}")
        worker_ok = False

    # 3) Scheduler startup: get_runner() and run_pipeline exist and are callable
    try:
        from amazon_research.scheduler import get_runner
        runner = get_runner()
        scheduler_ok = runner is not None and callable(getattr(runner, "run_pipeline", None))
    except Exception as e:
        print(f"scheduler startup FAIL: {e}")
        scheduler_ok = False

    # 4) Graceful shutdown: run runtime in thread, request shutdown via module flag, verify loop exits
    try:
        import threading
        from amazon_research import runtime_service
        result_holder = []

        def run_service():
            result_holder.append(
                runtime_service.run_runtime_service(
                    worker_interval_seconds=0.15,
                    worker_max_jobs_per_cycle=0,
                    pipeline_interval_seconds=0,
                )
            )

        th = threading.Thread(target=run_service, daemon=True)
        th.start()
        time.sleep(0.25)
        runtime_service._shutdown_requested = True
        th.join(timeout=2.0)
        shutdown_ok = not th.is_alive() and len(result_holder) == 1
        if result_holder and isinstance(result_holder[0], dict):
            shutdown_ok = shutdown_ok and result_holder[0].get("shutdown_requested") is True
    except Exception as e:
        print(f"graceful shutdown FAIL: {e}")
        shutdown_ok = False

    print("runtime service entrypoint OK" if (startup_ok and worker_ok and scheduler_ok and shutdown_ok) else "runtime service entrypoint FAIL")
    print("startup init: OK" if startup_ok else "startup init: FAIL")
    print("worker startup: OK" if worker_ok else "worker startup: FAIL")
    print("scheduler startup: OK" if scheduler_ok else "scheduler startup: FAIL")
    print("graceful shutdown: OK" if shutdown_ok else "graceful shutdown: FAIL")
    sys.exit(0 if (startup_ok and worker_ok and scheduler_ok and shutdown_ok) else 1)


if __name__ == "__main__":
    main()
