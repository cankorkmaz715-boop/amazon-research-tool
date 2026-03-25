#!/usr/bin/env python3
"""
Step 209 smoke test: Error recovery and failsafe execution layer.
Validates normal execution, fallback recovery, repeated failure suppression,
cooldown recovery, workspace isolation compatibility, stable payload behavior.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    from amazon_research.error_recovery import (
        run_with_failsafe,
        stable_failure_response,
        record_failure,
        record_success,
        is_suppressed,
        get_policy_summary,
        get_circuit_summary,
    )

    normal_ok = True
    fallback_ok = True
    suppression_ok = True
    cooldown_ok = True
    isolation_ok = True
    payload_ok = True

    # --- Normal execution path: run_with_failsafe runs fn and returns result on success
    try:
        out = run_with_failsafe(
            lambda: {"ok": True, "result": 42},
            workspace_id=99701,
            path_key="smoke_normal",
        )
        if not out.get("ok") or out.get("result") != 42:
            normal_ok = False
    except Exception as e:
        normal_ok = False
        print(f"normal execution path error: {e}")

    # --- Fallback recovery path: on failure, get_cached/get_persisted used if provided
    try:
        def failing_fn():
            raise RuntimeError("simulated failure")

        def get_cached():
            return {"ok": True, "result": "from_cache"}

        out = run_with_failsafe(
            failing_fn,
            workspace_id=99702,
            path_key="smoke_fallback",
            get_cached=get_cached,
        )
        if not out.get("ok") or out.get("result") != "from_cache":
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"fallback recovery path error: {e}")

    # --- Repeated failure suppression: after max failures, is_suppressed returns True
    try:
        path = "smoke_suppress"
        ws = 99703
        max_f = get_policy_summary().get("max_failures", 5)
        for _ in range(max_f + 1):
            record_failure(ws, path)
        suppressed, retry_after = is_suppressed(ws, path)
        if not suppressed or retry_after is None:
            suppression_ok = False
        record_success(ws, path)
        suppressed2, _ = is_suppressed(ws, path)
        if suppressed2:
            suppression_ok = False
    except Exception as e:
        suppression_ok = False
        print(f"repeated failure suppression error: {e}")

    # --- Cooldown recovery behavior: after cooldown, circuit allows again (or we clear with record_success)
    try:
        path = "smoke_cooldown"
        ws = 99704
        record_success(ws, path)
        suppressed, _ = is_suppressed(ws, path)
        if suppressed:
            cooldown_ok = False
        for _ in range(6):
            record_failure(ws, path)
        suppressed, retry = is_suppressed(ws, path)
        if not suppressed:
            cooldown_ok = False
        record_success(ws, path)
        suppressed, _ = is_suppressed(ws, path)
        if suppressed:
            cooldown_ok = False
    except Exception as e:
        cooldown_ok = False
        print(f"cooldown recovery error: {e}")

    # --- Workspace isolation compatibility: different workspace same path_key have separate counts
    try:
        record_success(99705, "shared_path")
        record_success(99706, "shared_path")
        for _ in range(6):
            record_failure(99705, "shared_path")
        s5, _ = is_suppressed(99705, "shared_path")
        s6, _ = is_suppressed(99706, "shared_path")
        if not s5 or s6:
            isolation_ok = False
        record_success(99705, "shared_path")
        record_success(99706, "shared_path")
    except Exception as e:
        isolation_ok = False
        print(f"workspace isolation error: {e}")

    # --- Stable payload behavior: stable_failure_response and run_with_failsafe return consistent shape
    try:
        fail = stable_failure_response(99707, "p", error="e", fallback_type="controlled_failure")
        if not isinstance(fail, dict) or "ok" not in fail or fail.get("ok") is not False:
            payload_ok = False
        if "error" not in fail or "fallback_type" not in fail:
            payload_ok = False
        out_no_fallback = run_with_failsafe(
            lambda: {"ok": False, "error": "intentional"},
            workspace_id=99708,
            path_key="payload_test",
        )
        if "ok" not in out_no_fallback:
            payload_ok = False
        summary = get_circuit_summary()
        if not isinstance(summary, dict):
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"stable payload error: {e}")

    print("error recovery and failsafe OK" if all([normal_ok, fallback_ok, suppression_ok, cooldown_ok, isolation_ok, payload_ok]) else "error recovery and failsafe FAIL")
    print("normal execution path: OK" if normal_ok else "normal execution path: FAIL")
    print("fallback recovery path: OK" if fallback_ok else "fallback recovery path: FAIL")
    print("repeated failure suppression: OK" if suppression_ok else "repeated failure suppression: FAIL")
    print("cooldown recovery behavior: OK" if cooldown_ok else "cooldown recovery behavior: FAIL")
    print("workspace isolation compatibility: OK" if isolation_ok else "workspace isolation compatibility: FAIL")
    print("stable payload behavior: OK" if payload_ok else "stable payload behavior: FAIL")
    sys.exit(0 if all([normal_ok, fallback_ok, suppression_ok, cooldown_ok, isolation_ok, payload_ok]) else 1)


if __name__ == "__main__":
    main()
