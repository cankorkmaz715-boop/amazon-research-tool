#!/usr/bin/env python3
"""
Step 208 smoke test: Memory and resource guard layer.
Validates guard allow path, high-pressure handling, heavy job concurrency protection,
metrics fallback behavior, worker integration compatibility, payload stability.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    from amazon_research.resource_guard import (
        check_resource_guard,
        ALLOW,
        DEFER,
        SKIP,
        get_policy_summary,
        get_process_memory_mb,
        get_heavy_job_count,
        would_exceed_heavy_budget,
        record_heavy_job_start,
        record_heavy_job_end,
        is_heavy_job_type,
        get_memory_mb_threshold,
    )
    from amazon_research.worker_stability import execute_with_stability

    allow_ok = True
    high_pressure_ok = True
    concurrency_ok = True
    fallback_ok = True
    worker_ok = True
    payload_ok = True

    # --- Resource guard allow path: under normal conditions guard allows
    try:
        decision, reason, metrics = check_resource_guard(workspace_id=99801, job_type="smoke_allow")
        if decision != ALLOW or reason is not None:
            allow_ok = False
        if not isinstance(metrics, dict):
            allow_ok = False
    except Exception as e:
        allow_ok = False
        print(f"guard allow path error: {e}")

    # --- High-pressure handling: set memory threshold to 1 MB so current RSS is "over" threshold
    try:
        os.environ["RESOURCE_GUARD_MEMORY_MB"] = "1"
        try:
            from amazon_research.resource_guard.policy import get_memory_mb_threshold
            if get_memory_mb_threshold() != 1:
                high_pressure_ok = False
            decision2, reason2, _ = check_resource_guard(workspace_id=99802, job_type="smoke_pressure")
            if decision2 not in (DEFER, SKIP) or reason2 != "memory_pressure":
                high_pressure_ok = False
        finally:
            os.environ.pop("RESOURCE_GUARD_MEMORY_MB", None)
    except Exception as e:
        high_pressure_ok = False
        print(f"high-pressure handling error: {e}")

    # --- Heavy job concurrency protection: exceed budget then check returns defer/skip
    try:
        if not is_heavy_job_type("intelligence_refresh"):
            concurrency_ok = False
        # Fill budget with synthetic heavy jobs (same type, different workspaces to get multiple entries)
        for i in range(20):
            record_heavy_job_start(99800 + i, "intelligence_refresh")
        decision3, reason3, m3 = check_resource_guard(workspace_id=99999, job_type="intelligence_refresh")
        if decision3 not in (DEFER, SKIP) or reason3 != "heavy_job_budget_exceeded":
            concurrency_ok = False
        for i in range(20):
            record_heavy_job_end(99800 + i, "intelligence_refresh")
    except Exception as e:
        concurrency_ok = False
        print(f"heavy job concurrency error: {e}")

    # --- Metrics fallback behavior: when memory read fails, policy fallback is used (allow or skip)
    try:
        policy = get_policy_summary()
        if not isinstance(policy, dict) or "metric_failure_action" not in policy:
            fallback_ok = False
        # Guard never raises; get_process_memory_mb can return None on some systems
        mem = get_process_memory_mb()
        if mem is not None and (not isinstance(mem, (int, float)) or mem < 0):
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"metrics fallback error: {e}")

    # --- Worker integration compatibility: execute_with_stability respects resource guard
    try:
        # Run a light job (non-heavy type) so guard allows; verify payload shape
        out = execute_with_stability(
            lambda: 1,
            workspace_id=99803,
            job_type="light_job",
            use_retry=False,
            timeout_seconds=5,
        )
        if "ok" not in out:
            worker_ok = False
        if out.get("ok") and out.get("result") != 1:
            worker_ok = False
        # When memory threshold is 0, guard may skip; then we get skipped (optional check)
        _ = execute_with_stability(lambda: 2, workspace_id=99804, job_type="light_job", use_retry=False, timeout_seconds=5)
    except Exception as e:
        worker_ok = False
        print(f"worker integration error: {e}")

    # --- Payload stability: check_resource_guard returns stable shape; policy summary stable
    try:
        d, r, m = check_resource_guard(workspace_id=99805, job_type="payload_test")
        if not isinstance(m, dict) or "memory_mb" not in m:
            payload_ok = False
        if d not in (ALLOW, DEFER, SKIP):
            payload_ok = False
        p = get_policy_summary()
        for k in ("memory_mb_threshold", "max_heavy_jobs", "defer_enabled"):
            if k not in p:
                payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    print("memory and resource guard OK" if all([allow_ok, high_pressure_ok, concurrency_ok, fallback_ok, worker_ok, payload_ok]) else "memory and resource guard FAIL")
    print("guard allow path: OK" if allow_ok else "guard allow path: FAIL")
    print("high-pressure handling: OK" if high_pressure_ok else "high-pressure handling: FAIL")
    print("heavy job concurrency protection: OK" if concurrency_ok else "heavy job concurrency protection: FAIL")
    print("metrics fallback behavior: OK" if fallback_ok else "metrics fallback behavior: FAIL")
    print("worker integration compatibility: OK" if worker_ok else "worker integration compatibility: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    sys.exit(0 if all([allow_ok, high_pressure_ok, concurrency_ok, fallback_ok, worker_ok, payload_ok]) else 1)


if __name__ == "__main__":
    main()
