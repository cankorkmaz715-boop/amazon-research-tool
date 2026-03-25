"""
Step 112: Operational health monitor – evaluate runtime system health from telemetry.
Rule-based: healthy, warning, critical. Compatible with worker, queue, crawler, scheduler, alert engine.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.health_monitor")

STATUS_HEALTHY = "healthy"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"


def _evaluate_worker_health(
    snapshot: Dict[str, Any],
    last_worker_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Worker health: liveness from last run summary; activity from telemetry."""
    if last_worker_summary is not None:
        processed = last_worker_summary.get("jobs_processed") or 0
        failed = last_worker_summary.get("jobs_failed") or 0
        if processed > 0 and failed >= processed:
            return {"status": STATUS_CRITICAL, "message": "worker last run had all jobs failed"}
        if processed > 0 and failed > 0:
            return {"status": STATUS_WARNING, "message": f"worker last run had {failed} failures"}
    return {"status": STATUS_HEALTHY, "message": "worker ok"}


def _evaluate_queue_health(
    queue_backlog: Optional[int],
    warning_threshold: int = 100,
    critical_threshold: int = 500,
) -> Dict[str, Any]:
    """Queue backlog health: healthy under warning_threshold, warning under critical, critical above."""
    if queue_backlog is None:
        return {"status": STATUS_HEALTHY, "message": "queue metrics unavailable"}
    if queue_backlog >= critical_threshold:
        return {"status": STATUS_CRITICAL, "message": f"queue backlog {queue_backlog} >= {critical_threshold}"}
    if queue_backlog >= warning_threshold:
        return {"status": STATUS_WARNING, "message": f"queue backlog {queue_backlog} >= {warning_threshold}"}
    return {"status": STATUS_HEALTHY, "message": f"queue backlog {queue_backlog}"}


def _evaluate_crawler_health(
    crawler_requests: int,
    crawler_success: int,
    crawler_failed: int,
    error_rate_warning: float = 0.2,
    error_rate_critical: float = 0.5,
) -> Dict[str, Any]:
    """Crawler health from error rate (failed / total requests)."""
    total = crawler_success + crawler_failed
    if total == 0:
        return {"status": STATUS_HEALTHY, "message": "no crawler activity yet"}
    rate = crawler_failed / total
    if rate >= error_rate_critical:
        return {"status": STATUS_CRITICAL, "message": f"crawler error rate {rate:.1%}"}
    if rate >= error_rate_warning:
        return {"status": STATUS_WARNING, "message": f"crawler error rate {rate:.1%}"}
    return {"status": STATUS_HEALTHY, "message": f"crawler error rate {rate:.1%}"}


def _evaluate_latency_health(
    refresh_latency_avg_ms: Optional[float],
    refresh_latency_count: int,
    warning_ms: float = 15000.0,
    critical_ms: float = 30000.0,
) -> Dict[str, Any]:
    """Refresh latency health: healthy under warning_ms, warning under critical_ms, critical above."""
    if refresh_latency_count == 0 or refresh_latency_avg_ms is None:
        return {"status": STATUS_HEALTHY, "message": "no refresh latency data yet"}
    if refresh_latency_avg_ms >= critical_ms:
        return {"status": STATUS_CRITICAL, "message": f"refresh avg latency {refresh_latency_avg_ms:.0f} ms"}
    if refresh_latency_avg_ms >= warning_ms:
        return {"status": STATUS_WARNING, "message": f"refresh avg latency {refresh_latency_avg_ms:.0f} ms"}
    return {"status": STATUS_HEALTHY, "message": f"refresh avg latency {refresh_latency_avg_ms:.0f} ms"}


def _evaluate_scheduler_health(
    last_worker_summary: Optional[Dict[str, Any]],
    plan_ok: bool = True,
) -> Dict[str, Any]:
    """Scheduler/worker liveness: plan_ok and worker has run or queue empty."""
    if not plan_ok:
        return {"status": STATUS_CRITICAL, "message": "scheduler plan failed"}
    if last_worker_summary is None:
        return {"status": STATUS_HEALTHY, "message": "scheduler ok (no worker summary)"}
    return {"status": STATUS_HEALTHY, "message": "scheduler ok"}


def get_operational_health(
    queue_warning_threshold: int = 100,
    queue_critical_threshold: int = 500,
    crawler_error_warning: float = 0.2,
    crawler_error_critical: float = 0.5,
    latency_warning_ms: float = 15000.0,
    latency_critical_ms: float = 30000.0,
) -> Dict[str, Any]:
    """
    Evaluate operational health from telemetry and scheduler. Returns structured output:
    overall (healthy|warning|critical), components (worker, queue, crawler, latency, scheduler each with status, message).
    """
    try:
        from amazon_research.monitoring.runtime_metrics import get_metrics_snapshot
        snapshot = get_metrics_snapshot()
    except Exception as e:
        logger.debug("health_monitor: get_metrics_snapshot failed: %s", e)
        snapshot = {}

    last_worker_summary = None
    try:
        from amazon_research.scheduler import get_last_worker_run_summary
        last_worker_summary = get_last_worker_run_summary()
    except Exception:
        pass

    plan_ok = True
    try:
        from amazon_research.scheduler import plan_discovery_tasks
        plan = plan_discovery_tasks(max_category_tasks=0, max_keyword_tasks=0, include_niche_discovery=True, include_alert_refresh=True)
        plan_ok = "schedule" in plan and "summary" in plan
    except Exception:
        plan_ok = False

    worker = _evaluate_worker_health(snapshot, last_worker_summary)
    queue = _evaluate_queue_health(
        snapshot.get("queue_backlog"),
        warning_threshold=queue_warning_threshold,
        critical_threshold=queue_critical_threshold,
    )
    crawler = _evaluate_crawler_health(
        snapshot.get("crawler_requests") or 0,
        snapshot.get("crawler_success") or 0,
        snapshot.get("crawler_failed") or 0,
        error_rate_warning=crawler_error_warning,
        error_rate_critical=crawler_error_critical,
    )
    latency = _evaluate_latency_health(
        snapshot.get("refresh_latency_avg_ms"),
        snapshot.get("refresh_latency_count") or 0,
        warning_ms=latency_warning_ms,
        critical_ms=latency_critical_ms,
    )
    scheduler = _evaluate_scheduler_health(last_worker_summary, plan_ok)

    components = {
        "worker": worker,
        "queue": queue,
        "crawler": crawler,
        "latency": latency,
        "scheduler": scheduler,
    }

    statuses = [c["status"] for c in components.values()]
    if STATUS_CRITICAL in statuses:
        overall = STATUS_CRITICAL
    elif STATUS_WARNING in statuses:
        overall = STATUS_WARNING
    else:
        overall = STATUS_HEALTHY

    return {
        "overall": overall,
        "components": components,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
