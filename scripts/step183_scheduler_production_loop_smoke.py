#!/usr/bin/env python3
"""Step 183: Scheduler production loop – cycle scheduling, job coordination, runtime compatibility."""
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    cycle_scheduling_ok = False
    job_coordination_ok = False
    runtime_compat_ok = False

    # 1) Cycle scheduling: run_production_scheduler_tick with custom intervals (only lightweight cycles due)
    try:
        from amazon_research.scheduler.production_loop import (
            run_production_scheduler_tick,
            get_production_loop_status,
            CYCLE_SIGNAL_UPDATE,
            CYCLE_ANOMALY_MONITORING,
            CYCLE_DISCOVERY,
            CYCLE_REFRESH,
            CYCLE_OPPORTUNITY_SCORING,
        )
        # Use very large intervals so only lightweight cycles (signal_update, anomaly) run without DB
        huge = 1e10
        intervals = {
            CYCLE_DISCOVERY: huge,
            CYCLE_REFRESH: huge,
            CYCLE_SIGNAL_UPDATE: 0,
            CYCLE_OPPORTUNITY_SCORING: huge,
            CYCLE_ANOMALY_MONITORING: 0,
        }
        result = run_production_scheduler_tick(now=time.time(), intervals=intervals)
        cycles_run = result.get("cycles_run") or []
        cycle_scheduling_ok = (
            isinstance(result, dict)
            and "cycles_run" in result
            and "cycles_skipped" in result
            and "tick_at" in result
            and len(cycles_run) >= 1
        )
        if cycles_run:
            cycle_scheduling_ok = cycle_scheduling_ok and all(
                r.get("cycle") and "duration_seconds" in r and "completed" in r
                for r in cycles_run
            )
    except Exception as e:
        print(f"cycle scheduling FAIL: {e}")
        cycle_scheduling_ok = False

    # 2) Job coordination: status shows cycle state; no overlap (running false after tick)
    try:
        status = get_production_loop_status()
        job_coordination_ok = (
            isinstance(status, dict)
            and "cycle_last_run" in status
            and "cycle_running" in status
            and "intervals" in status
        )
        if job_coordination_ok and status.get("cycle_running"):
            running = status["cycle_running"]
            job_coordination_ok = not any(running.values())
    except Exception as e:
        print(f"job coordination FAIL: {e}")
        job_coordination_ok = False

    # 3) Runtime compatibility: runtime_service and production_loop coexist; tick can be called
    try:
        from amazon_research import runtime_service
        from amazon_research.scheduler import run_production_scheduler_tick as tick
        _ = runtime_service.get_runtime_status()
        huge = 1e10
        r = tick(now=time.time(), intervals={CYCLE_SIGNAL_UPDATE: 0, CYCLE_ANOMALY_MONITORING: huge, CYCLE_DISCOVERY: huge, CYCLE_REFRESH: huge, CYCLE_OPPORTUNITY_SCORING: huge})
        runtime_compat_ok = isinstance(r, dict) and "cycles_run" in r
    except Exception as e:
        print(f"runtime compatibility FAIL: {e}")
        runtime_compat_ok = False

    all_ok = cycle_scheduling_ok and job_coordination_ok and runtime_compat_ok
    print("scheduler production loop OK" if all_ok else "scheduler production loop FAIL")
    print("cycle scheduling: OK" if cycle_scheduling_ok else "cycle scheduling: FAIL")
    print("job coordination: OK" if job_coordination_ok else "job coordination: FAIL")
    print("runtime compatibility: OK" if runtime_compat_ok else "runtime compatibility: FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
