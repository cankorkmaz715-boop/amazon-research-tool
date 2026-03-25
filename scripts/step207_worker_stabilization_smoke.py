#!/usr/bin/env python3
"""
Step 207 smoke test: Worker stabilization and queue safety.
Validates worker job execution, retry mechanism, duplicate job suppression,
job locking, worker recovery after failure, payload stability.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    from amazon_research.worker_stability import (
        execute_with_stability,
        try_acquire,
        release,
        release_force,
        run_with_retry,
        get_retry_max_attempts,
        get_job_timeout_seconds,
        get_policy_summary,
        get_active_count,
        get_health_summary,
        would_starve,
    )

    worker_ok = True
    retry_ok = True
    duplicate_ok = True
    locking_ok = True
    recovery_ok = True
    payload_ok = True

    # --- Worker job execution: execute_with_stability runs fn and returns stable shape
    try:
        out = execute_with_stability(lambda: 42, workspace_id=99901, job_type="smoke_test", use_retry=False, timeout_seconds=5)
        if not out.get("ok") or out.get("result") != 42:
            worker_ok = False
        if "result" not in out and out.get("ok"):
            worker_ok = False
    except Exception as e:
        worker_ok = False
        print(f"worker job execution error: {e}")

    # --- Retry mechanism: run_with_retry retries on failure, respects max
    try:
        attempts = []

        def failing_twice():
            attempts.append(1)
            if len(attempts) < 2:
                raise ValueError("simulated")
            return "ok"

        result = run_with_retry(failing_twice, workspace_id=99902, job_type="retry_test", max_attempts=3, backoff_base_seconds=0)
        if not result.get("ok") or result.get("result") != "ok" or len(attempts) != 2:
            retry_ok = False
        result_fail = run_with_retry(lambda: (_ for _ in ()).throw(ValueError("permanent")), workspace_id=99902, job_type="retry_fail", max_attempts=2, backoff_base_seconds=0)
        if result_fail.get("ok") or result_fail.get("attempts") != 2:
            retry_ok = False
    except Exception as e:
        retry_ok = False
        print(f"retry mechanism error: {e}")

    # --- Duplicate job suppression: second acquire for same (workspace, job_type) fails
    try:
        ac1, lid1 = try_acquire(99903, "dup_test")
        ac2, lid2 = try_acquire(99903, "dup_test")
        if not ac1 or ac2 or lid2 is not None:
            duplicate_ok = False
        release(99903, "dup_test", lid1)
        ac3, lid3 = try_acquire(99903, "dup_test")
        if not ac3:
            duplicate_ok = False
        release(99903, "dup_test", lid3)
    except Exception as e:
        duplicate_ok = False
        print(f"duplicate job suppression error: {e}")

    # --- Job locking behavior: acquire/release and release_force
    try:
        ac, lock_id = try_acquire(99904, "lock_test")
        if not ac or not lock_id:
            locking_ok = False
        released = release(99904, "lock_test", lock_id)
        if not released:
            locking_ok = False
        ac2, _ = try_acquire(99904, "lock_test")
        if not ac2:
            locking_ok = False
        release_force(99904, "lock_test")
        policy = get_policy_summary()
        if not isinstance(policy, dict) or "retry_max_attempts" not in policy:
            locking_ok = False
    except Exception as e:
        locking_ok = False
        print(f"job locking error: {e}")

    # --- Worker recovery after failure: execute_with_stability returns ok=False and does not crash
    try:
        out_fail = execute_with_stability(
            lambda: (_ for _ in ()).throw(RuntimeError("crash")),
            workspace_id=99905,
            job_type="crash_test",
            use_lock=False,
            use_retry=False,
            timeout_seconds=5,
        )
        if out_fail.get("ok"):
            recovery_ok = False
        if "error" not in out_fail:
            recovery_ok = False
    except Exception:
        recovery_ok = False

    # --- Payload stability: all execution results have consistent shape
    try:
        for ws, jt in [(99906, "a"), (99907, "b")]:
            o = execute_with_stability(lambda: None, workspace_id=ws, job_type=jt, use_retry=False, timeout_seconds=5)
            if "ok" not in o:
                payload_ok = False
            if o.get("ok") and "result" not in o:
                payload_ok = False
        health = get_health_summary()
        if not isinstance(health, dict) or "active_job_count" not in health:
            payload_ok = False
        _ = get_active_count()
        _ = would_starve()
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    print("worker stabilization OK" if all([worker_ok, retry_ok, duplicate_ok, locking_ok, recovery_ok, payload_ok]) else "worker stabilization FAIL")
    print("worker job execution: OK" if worker_ok else "worker job execution: FAIL")
    print("retry mechanism: OK" if retry_ok else "retry mechanism: FAIL")
    print("duplicate job suppression: OK" if duplicate_ok else "duplicate job suppression: FAIL")
    print("job locking behavior: OK" if locking_ok else "job locking behavior: FAIL")
    print("worker recovery: OK" if recovery_ok else "worker recovery: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    sys.exit(0 if all([worker_ok, retry_ok, duplicate_ok, locking_ok, recovery_ok, payload_ok]) else 1)


if __name__ == "__main__":
    main()
