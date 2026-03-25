"""
Step 113: Runtime alert routing – route alerts/health events to targets (dashboard, ops).
Rule-based; no outbound delivery. Consumes health monitor, opportunity alerts, worker/queue, quota events.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.alert_routing")

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

SOURCE_HEALTH_MONITOR = "health_monitor"
SOURCE_OPPORTUNITY_ALERT = "opportunity_alert"
SOURCE_WORKER_QUEUE = "worker_queue"
SOURCE_QUOTA = "quota"

ROUTE_TARGET_DASHBOARD = "dashboard"
ROUTE_TARGET_OPS = "ops"
ROUTE_TARGET_NOTIFICATION = "notification"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _routing_record(
    alert_id: str,
    route_target_type: str,
    route_reason: str,
    severity: str,
    timestamp: str,
    *,
    source_type: Optional[str] = None,
    workspace_id: Optional[int] = None,
    alert_category: Optional[str] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "alert_id": alert_id,
        "route_target_type": route_target_type,
        "route_reason": route_reason,
        "severity": severity,
        "timestamp": timestamp,
    }
    if source_type is not None:
        out["source_type"] = source_type
    if workspace_id is not None:
        out["workspace_id"] = workspace_id
    if alert_category is not None:
        out["alert_category"] = alert_category
    return out


def _severity_to_target(severity: str) -> str:
    if severity == SEVERITY_CRITICAL:
        return ROUTE_TARGET_OPS
    return ROUTE_TARGET_DASHBOARD


def route_health_event(
    health_result: Dict[str, Any],
    *,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Produce routing records from operational health output. One record per non-healthy component
    (or one overall if overall is not healthy). Severity from health status; route_target from severity.
    """
    records: List[Dict[str, Any]] = []
    overall = (health_result.get("overall") or "").strip() or "healthy"
    components = health_result.get("components") or {}
    ts = health_result.get("evaluated_at") or _now_iso()
    alert_id = str(uuid.uuid4())

    if overall == "critical":
        severity = SEVERITY_CRITICAL
        reason = "operational health critical"
        for name, comp in components.items():
            if (comp or {}).get("status") == "critical":
                reason = (comp or {}).get("message") or reason
                break
        records.append(_routing_record(
            alert_id, _severity_to_target(severity), reason, severity, ts,
            source_type=SOURCE_HEALTH_MONITOR, workspace_id=workspace_id, alert_category="health",
        ))
    elif overall == "warning":
        severity = SEVERITY_WARNING
        reason = "operational health warning"
        for name, comp in components.items():
            if (comp or {}).get("status") == "warning":
                reason = (comp or {}).get("message") or reason
                break
        records.append(_routing_record(
            alert_id, _severity_to_target(severity), reason, severity, ts,
            source_type=SOURCE_HEALTH_MONITOR, workspace_id=workspace_id, alert_category="health",
        ))
    return records


def route_opportunity_alert(
    alert: Dict[str, Any],
    *,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Produce one routing record per opportunity alert. Severity: warning by default."""
    alert_id = (alert.get("alert_id") or str(uuid.uuid4()))
    if isinstance(alert_id, str) and not alert_id:
        alert_id = str(uuid.uuid4())
    ts = alert.get("timestamp") or _now_iso()
    severity = SEVERITY_WARNING
    signals = alert.get("triggering_signals") or {}
    reason = (signals.get("reason") or alert.get("alert_type") or "opportunity_alert")
    if isinstance(reason, dict):
        reason = str(reason)
    category = alert.get("alert_type") or "opportunity"
    target = _severity_to_target(severity)
    return [_routing_record(
        str(alert_id), target, reason, severity, ts,
        source_type=SOURCE_OPPORTUNITY_ALERT, workspace_id=workspace_id, alert_category=category,
    )]


def route_worker_event(
    event: Dict[str, Any],
    *,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Produce one routing record for a worker/queue event (e.g. job_failed)."""
    event_type = (event.get("event_type") or "job_event").strip()
    severity = SEVERITY_WARNING if event_type in ("job_failed", "job_timeout") else SEVERITY_INFO
    reason = event.get("message") or event.get("error") or event_type
    if isinstance(reason, dict):
        reason = str(reason)
    wid = event.get("workspace_id") if event.get("workspace_id") is not None else workspace_id
    ts = event.get("timestamp") or _now_iso()
    return [_routing_record(
        str(uuid.uuid4()), _severity_to_target(severity), reason, severity, ts,
        source_type=SOURCE_WORKER_QUEUE, workspace_id=wid, alert_category=event_type,
    )]


def route_quota_event(
    event: Dict[str, Any],
    *,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Produce one routing record for quota or rate-limit event."""
    severity = SEVERITY_CRITICAL
    reason = event.get("message") or event.get("quota_type") or event.get("bucket") or "quota_exceeded"
    if isinstance(reason, dict):
        reason = str(reason)
    wid = event.get("workspace_id") if event.get("workspace_id") is not None else workspace_id
    ts = event.get("timestamp") or _now_iso()
    return [_routing_record(
        str(uuid.uuid4()), _severity_to_target(severity), reason, severity, ts,
        source_type=SOURCE_QUOTA, workspace_id=wid, alert_category="quota",
    )]


def route_event(
    event: Dict[str, Any],
    source_type: str,
    *,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Single entry point: route an event by source_type. Returns list of routing records.
    source_type: health_monitor | opportunity_alert | worker_queue | quota.
    """
    st = (source_type or "").strip()
    if st == SOURCE_HEALTH_MONITOR:
        return route_health_event(event, workspace_id=workspace_id)
    if st == SOURCE_OPPORTUNITY_ALERT:
        return route_opportunity_alert(event, workspace_id=workspace_id)
    if st == SOURCE_WORKER_QUEUE:
        return route_worker_event(event, workspace_id=workspace_id)
    if st == SOURCE_QUOTA:
        return route_quota_event(event, workspace_id=workspace_id)
    logger.debug("alert_routing unknown source_type %r", source_type)
    return []
