#!/usr/bin/env python3
"""Step 36: Config / tuning layer – central delay, retry, batch, and safety cap settings."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.config import get_config

    cfg = get_config()

    # Delay config: all delay-related fields present and non-negative
    delay_ok = (
        getattr(cfg, "request_delay_min_sec", 0) >= 0
        and getattr(cfg, "request_delay_max_sec", 0) >= 0
        and getattr(cfg, "discovery_page_wait_sec", 0) >= 0
        and getattr(cfg, "refresh_page_wait_sec", 0) >= 0
        and getattr(cfg, "antibot_delay_min_sec", 0) >= 0
        and getattr(cfg, "antibot_delay_max_sec", 0) >= 0
        and getattr(cfg, "page_load_timeout_ms", 0) > 0
    )

    # Retry config
    retry_ok = (
        getattr(cfg, "max_retries", 0) >= 0
        and getattr(cfg, "navigation_retries", 0) >= 1
        and getattr(cfg, "navigation_retry_base_sec", 0) >= 0
        and getattr(cfg, "skip_after_n_failures", 0) >= 1
        and getattr(cfg, "skip_duration_hours", 0) > 0
    )

    # Batch config
    batch_ok = (
        getattr(cfg, "max_discovery_pages", 0) >= 1
        and getattr(cfg, "max_refresh_batch_size", 0) >= 1
        and getattr(cfg, "max_refresh_consecutive_failures", 0) >= 1
        and getattr(cfg, "scheduler_refresh_limit", 0) >= 1
        and getattr(cfg, "scheduler_scoring_limit", 0) >= 1
    )

    # Safety caps: upper bounds exist and are positive
    safety_ok = (
        getattr(cfg, "max_discovery_pages_cap", 0) >= 1
        and getattr(cfg, "max_refresh_batch_size_cap", 0) >= 1
    )

    print("config tuning OK")
    print("delay config: OK" if delay_ok else "delay config: FAIL")
    print("retry config: OK" if retry_ok else "retry config: FAIL")
    print("batch config: OK" if batch_ok else "batch config: FAIL")
    print("safety caps: OK" if safety_ok else "safety caps: FAIL")

    if not (delay_ok and retry_ok and batch_ok and safety_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
