"""
Step 111: System telemetry layer – runtime metrics for crawler, worker, queue, discovery, refresh, alerts.
In-memory first; lightweight and safe for high-frequency updates. Optional persistence hooks later.
"""
import threading
import time
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.runtime_metrics")

_lock = threading.Lock()
_crawler_requests = 0
_crawler_success = 0
_crawler_failed = 0
_worker_jobs_processed = 0
_discovery_runs = 0
_refresh_latency_sum_ms: float = 0.0
_refresh_latency_count = 0
_alert_generated_count = 0


def record_crawler_request() -> None:
    """Record one crawler request (category or keyword page fetch)."""
    global _crawler_requests
    with _lock:
        _crawler_requests += 1


def record_crawler_success() -> None:
    """Record one successful crawler response."""
    global _crawler_success
    with _lock:
        _crawler_success += 1


def record_crawler_failure() -> None:
    """Record one failed crawler request."""
    global _crawler_failed
    with _lock:
        _crawler_failed += 1


def record_worker_job_processed(success: bool = True) -> None:
    """Record one worker job processed (completed or failed)."""
    global _worker_jobs_processed
    with _lock:
        _worker_jobs_processed += 1


def record_discovery_run() -> None:
    """Record one discovery run (category scan, keyword scan, or niche discovery)."""
    global _discovery_runs
    with _lock:
        _discovery_runs += 1


def record_refresh_latency_ms(latency_ms: float) -> None:
    """Record refresh latency in milliseconds (e.g. per-ASIN or batch)."""
    global _refresh_latency_sum_ms, _refresh_latency_count
    with _lock:
        _refresh_latency_sum_ms += max(0.0, float(latency_ms))
        _refresh_latency_count += 1


def record_alert_generated(count: int = 1) -> None:
    """Record alert generation (e.g. number of alerts produced)."""
    global _alert_generated_count
    with _lock:
        _alert_generated_count += max(0, count)


def get_queue_backlog() -> Optional[Dict[str, Any]]:
    """Return current queue metrics (queued_count, etc.) from DB if available; else None."""
    try:
        from amazon_research.db import get_queue_metrics
        return get_queue_metrics()
    except Exception:
        return None


def get_metrics_snapshot() -> Dict[str, Any]:
    """
    Return a snapshot of all runtime metrics. Queue backlog from DB when available.
    Safe for dashboards, health panels, operational alerts.
    """
    with _lock:
        crawler_requests = _crawler_requests
        crawler_success = _crawler_success
        crawler_failed = _crawler_failed
        worker_jobs_processed = _worker_jobs_processed
        discovery_runs = _discovery_runs
        refresh_latency_sum_ms = _refresh_latency_sum_ms
        refresh_latency_count = _refresh_latency_count
        alert_generated_count = _alert_generated_count

    queue = get_queue_backlog()
    queue_backlog = queue.get("queued_count") if isinstance(queue, dict) else None

    refresh_avg_ms = (refresh_latency_sum_ms / refresh_latency_count) if refresh_latency_count else None

    return {
        "crawler_requests": crawler_requests,
        "crawler_success": crawler_success,
        "crawler_failed": crawler_failed,
        "worker_jobs_processed": worker_jobs_processed,
        "queue_backlog": queue_backlog,
        "discovery_runs": discovery_runs,
        "refresh_latency_sum_ms": round(refresh_latency_sum_ms, 2),
        "refresh_latency_count": refresh_latency_count,
        "refresh_latency_avg_ms": round(refresh_avg_ms, 2) if refresh_avg_ms is not None else None,
        "alert_generated_count": alert_generated_count,
    }


def reset_runtime_metrics() -> None:
    """Reset all runtime counters (e.g. for tests or periodic rollover)."""
    global _crawler_requests, _crawler_success, _crawler_failed
    global _worker_jobs_processed, _discovery_runs
    global _refresh_latency_sum_ms, _refresh_latency_count, _alert_generated_count
    with _lock:
        _crawler_requests = 0
        _crawler_success = 0
        _crawler_failed = 0
        _worker_jobs_processed = 0
        _discovery_runs = 0
        _refresh_latency_sum_ms = 0.0
        _refresh_latency_count = 0
        _alert_generated_count = 0
