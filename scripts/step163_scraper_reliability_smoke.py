#!/usr/bin/env python3
"""Step 163: Scraper reliability layer – retry, proxy rotation, response validation, throttling, failure tracking."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.monitoring.scraper_reliability import (
        get_retry_delay,
        retry_controller,
        should_rotate_proxy,
        proxy_rotation_guard,
        response_validation,
        request_throttling,
        record_request,
        scrape_failure_tracker_record,
        scrape_failure_tracker_summary,
        recovery_scheduler_add,
        recovery_scheduler_pending,
        recovery_scheduler_mark_retried,
        get_scraper_reliability_status,
        FAILURE_NETWORK,
        FAILURE_BLOCKED,
    )

    # 1) Retry system: exponential backoff 2s, 5s, 10s for attempts 0, 1, 2
    d0 = get_retry_delay(0)
    d1 = get_retry_delay(1)
    d2 = get_retry_delay(2)
    retry_ok = d0 == 2.0 and d1 == 5.0 and d2 == 10.0
    n = [0]
    try:
        retry_controller(lambda: (n.append(1) or 1 / 0), max_attempts=2, on_retry=lambda a, e: None)
    except ZeroDivisionError:
        retry_ok = retry_ok and n[-1] == 1

    # 2) Proxy rotation: rotate on timeout/block
    proxy_ok = should_rotate_proxy("timeout") is True and should_rotate_proxy("connection_fail") is True
    guard = proxy_rotation_guard("timeout")
    proxy_ok = proxy_ok and guard.get("rotate_recommended") is True and "status" in guard

    # 3) Response validation: empty -> invalid, captcha-like -> invalid, normal HTML -> valid
    r_empty = response_validation("")
    r_captcha = response_validation("<html><body>Please complete the captcha</body></html>")
    normal_html = "<html><body><div>Product data here</div></body></html>"
    r_ok = response_validation(normal_html)
    validation_ok = (
        r_empty.get("valid") is False
        and r_captcha.get("valid") is False
        and r_ok.get("valid") is True
        and "reason" in r_ok
    )

    # 4) Request throttling: returns can_send, wait_seconds
    t = request_throttling("example.com", max_per_minute=30, cooldown_seconds=0)
    throttling_ok = "can_send" in t and "wait_seconds" in t and "status" in t
    record_request("example.com")

    # 5) Failure tracking: record and summary
    scrape_failure_tracker_record(FAILURE_NETWORK, {"url": "https://example.com"})
    scrape_failure_tracker_record(FAILURE_BLOCKED)
    summary = scrape_failure_tracker_summary(limit=10)
    failure_ok = "by_category" in summary and "status" in summary and summary.get("status") == "OK"

    # 6) Recovery scheduler: add, pending, mark_retried
    task_id = recovery_scheduler_add({"url": "https://example.com/page", "reason": "timeout"})
    pending = recovery_scheduler_pending(limit=5)
    recovery_ok = isinstance(task_id, str) and len(task_id) > 0 and isinstance(pending, list)
    recovery_ok = recovery_ok and recovery_scheduler_mark_retried(task_id) is True
    recovery_ok = recovery_ok and recovery_scheduler_mark_retried("nonexistent") is False

    # Aggregate status
    status = get_scraper_reliability_status()
    status_ok = (
        status.get("scraper_status") == "OK"
        and status.get("retry_system") == "OK"
        and status.get("proxy_rotation") == "OK"
        and status.get("response_validation") == "OK"
        and status.get("throttling") == "OK"
        and status.get("failure_tracking") == "OK"
    )

    print("scraper reliability layer OK")
    print("retry system: OK" if retry_ok else "retry system: FAIL")
    print("proxy rotation: OK" if proxy_ok else "proxy rotation: FAIL")
    print("response validation: OK" if validation_ok else "response validation: FAIL")
    print("request throttling: OK" if throttling_ok else "request throttling: FAIL")
    print("failure tracking: OK" if failure_ok else "failure tracking: FAIL")

    if not (retry_ok and proxy_ok and validation_ok and throttling_ok and failure_ok and recovery_ok and status_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
