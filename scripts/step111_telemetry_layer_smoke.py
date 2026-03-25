#!/usr/bin/env python3
"""Step 111: System telemetry layer – crawler, worker, queue, discovery, alert metrics."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import (
        record_crawler_request,
        record_crawler_success,
        record_crawler_failure,
        record_worker_job_processed,
        record_discovery_run,
        record_refresh_latency_ms,
        record_alert_generated,
        get_metrics_snapshot,
        reset_runtime_metrics,
    )

    reset_runtime_metrics()

    record_crawler_request()
    record_crawler_request()
    record_crawler_success()
    record_crawler_failure()
    record_worker_job_processed(success=True)
    record_worker_job_processed(success=False)
    record_discovery_run()
    record_refresh_latency_ms(150.5)
    record_refresh_latency_ms(200.0)
    record_alert_generated(3)

    snap = get_metrics_snapshot()

    crawler_ok = (
        snap.get("crawler_requests") == 2
        and snap.get("crawler_success") == 1
        and snap.get("crawler_failed") == 1
    )
    worker_ok = snap.get("worker_jobs_processed") == 2
    queue_ok = "queue_backlog" in snap
    discovery_ok = snap.get("discovery_runs") == 1
    alert_ok = snap.get("alert_generated_count") == 3

    refresh_ok = (
        snap.get("refresh_latency_count") == 2
        and snap.get("refresh_latency_sum_ms") is not None
    )

    print("telemetry layer OK")
    print("crawler metrics: OK" if crawler_ok else "crawler metrics: FAIL")
    print("worker metrics: OK" if worker_ok else "worker metrics: FAIL")
    print("queue metrics: OK" if queue_ok else "queue metrics: FAIL")
    print("discovery metrics: OK" if discovery_ok else "discovery metrics: FAIL")
    print("alert metrics: OK" if alert_ok else "alert metrics: FAIL")

    if not (crawler_ok and worker_ok and queue_ok and discovery_ok and alert_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
