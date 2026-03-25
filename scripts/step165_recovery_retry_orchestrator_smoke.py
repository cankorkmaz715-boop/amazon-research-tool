#!/usr/bin/env python3
"""Step 165: Recovery / Retry Orchestrator v2 – failure classification, recovery action, cooldown, scheduler compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.monitoring.recovery_retry_orchestrator_v2 import (
        classify_failure,
        record_target_failure,
        get_target_failure_count,
        get_recovery_decision,
        apply_failure_and_get_decision,
        FAILURE_TEMPORARY_NETWORK,
        FAILURE_PROXY,
        FAILURE_BLOCKED_CAPTCHA,
        FAILURE_PARSER,
        FAILURE_REPEATED_TARGET,
        ACTION_IMMEDIATE_RETRY,
        ACTION_DELAYED_RETRY,
        ACTION_PROXY_ROTATION_BEFORE_RETRY,
        ACTION_SKIP_ESCALATE,
    )

    # 1) Failure classification: raw type / message -> category
    c1 = classify_failure("timeout", None)
    c2 = classify_failure("proxy_error", None)
    c3 = classify_failure(None, "page returned captcha")
    c4 = classify_failure("parser_error", None)
    classification_ok = c1 == FAILURE_TEMPORARY_NETWORK and c2 == FAILURE_PROXY
    classification_ok = classification_ok and c3 == FAILURE_BLOCKED_CAPTCHA and c4 == FAILURE_PARSER

    # 2) Recovery action selection: decision has recovery_action_chosen, retry_schedule, cooldown_info
    d1 = get_recovery_decision("target-1", FAILURE_TEMPORARY_NETWORK, attempt=0)
    d2 = get_recovery_decision("target-2", FAILURE_PROXY, attempt=1)
    d3 = get_recovery_decision("target-3", FAILURE_BLOCKED_CAPTCHA)
    action_ok = d1.get("recovery_action_chosen") in (ACTION_IMMEDIATE_RETRY, ACTION_DELAYED_RETRY)
    action_ok = action_ok and d2.get("recovery_action_chosen") == ACTION_PROXY_ROTATION_BEFORE_RETRY
    action_ok = action_ok and "retry_schedule" in d1 and "cooldown_info" in d1
    action_ok = action_ok and d3.get("detected_failure_category") == FAILURE_BLOCKED_CAPTCHA

    # 3) Cooldown handling: repeated failures -> skip_escalate, cooldown_info set
    tid = "target-repeated-165"
    for _ in range(3):
        record_target_failure(tid)
    d_repeated = get_recovery_decision(tid, None, None, None, attempt=0)
    # After 3 recorded failures, category should be repeated and action skip_escalate
    repeated_category = get_target_failure_count(tid) >= 3
    cooldown_ok = "cooldown_info" in d_repeated
    cooldown_ok = cooldown_ok and (d_repeated.get("recovery_action_chosen") == ACTION_SKIP_ESCALATE or not repeated_category)
    if repeated_category:
        cooldown_ok = cooldown_ok and (d_repeated.get("detected_failure_category") == FAILURE_REPEATED_TARGET or d_repeated.get("recovery_action_chosen") == ACTION_SKIP_ESCALATE)

    # 4) Scheduler compatibility: decision structure usable by worker/scheduler (target_id, retry_schedule)
    applied = apply_failure_and_get_decision("target-sched", "timeout", "connection timed out", job_id=99, attempt=0)
    compat_ok = applied.get("target_id") == "target-sched" and applied.get("failed_job_id") == 99
    compat_ok = compat_ok and "retry_schedule" in applied and "timestamp" in applied
    compat_ok = compat_ok and applied.get("detected_failure_category") == FAILURE_TEMPORARY_NETWORK

    print("recovery retry orchestrator v2 OK")
    print("failure classification: OK" if classification_ok else "failure classification: FAIL")
    print("recovery action selection: OK" if action_ok else "recovery action selection: FAIL")
    print("cooldown handling: OK" if cooldown_ok else "cooldown handling: FAIL")
    print("scheduler compatibility: OK" if compat_ok else "scheduler compatibility: FAIL")

    if not (classification_ok and action_ok and cooldown_ok and compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
