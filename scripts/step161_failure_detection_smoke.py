#!/usr/bin/env python3
"""Step 161: Platform failure detector – scraper, proxy, parser, signal, scoring, scheduler health checks."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring.platform_failure_detector import (
        scraper_health_check,
        proxy_connection_check,
        parser_integrity_check,
        signal_integrity_check,
        scoring_sanity_check,
        scheduler_job_check,
        STATUS_OK,
        STATUS_WARNING,
        STATUS_FAIL,
    )

    # Each check returns { status, component, reason, severity }
    def valid_report(r):
        return (
            r.get("status") in (STATUS_OK, STATUS_WARNING, STATUS_FAIL)
            and r.get("component")
            and "reason" in r
            and r.get("severity") in ("low", "medium", "high")
        )

    scraper = scraper_health_check()
    proxy = proxy_connection_check()
    parser = parser_integrity_check()
    signal = signal_integrity_check(sample_size=10)
    scoring = scoring_sanity_check(sample_size=10)
    scheduler = scheduler_job_check(limit=10)

    scraper_ok = valid_report(scraper)
    proxy_ok = valid_report(proxy)
    parser_ok = valid_report(parser) and parser.get("status") == STATUS_OK
    signal_ok = valid_report(signal)
    scoring_ok = valid_report(scoring)
    scheduler_ok = valid_report(scheduler)

    print("platform failure detector OK")
    print("scraper health: OK" if scraper_ok else "scraper health: FAIL")
    print("proxy health: OK" if proxy_ok else "proxy health: FAIL")
    print("parser integrity: OK" if parser_ok else "parser integrity: FAIL")
    print("signal integrity: OK" if signal_ok else "signal integrity: FAIL")
    print("scoring sanity: OK" if scoring_ok else "scoring sanity: FAIL")
    print("scheduler health: OK" if scheduler_ok else "scheduler health: FAIL")

    if not (scraper_ok and proxy_ok and parser_ok and signal_ok and scoring_ok and scheduler_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
