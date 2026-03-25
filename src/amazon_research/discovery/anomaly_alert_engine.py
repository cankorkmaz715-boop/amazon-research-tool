"""
Step 173: Anomaly alert engine – detect unusual or abnormal changes in opportunity-related signals.
Anomaly types: sudden trend spike, opportunity score collapse, competition surge, demand breakdown,
unusual lifecycle transition. Uses signal drift detector, lifecycle engine, trend/demand/competition history.
Integrates with alert prioritization, workspace opportunity feed, research dashboard.
Lightweight, deterministic, rule-based. Extensible for anomaly analytics and automated interventions.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.anomaly_alert_engine")

# Anomaly types
ANOMALY_TREND_SPIKE = "sudden_trend_spike"
ANOMALY_SCORE_COLLAPSE = "opportunity_score_collapse"
ANOMALY_COMPETITION_SURGE = "competition_surge"
ANOMALY_DEMAND_BREAKDOWN = "demand_breakdown"
ANOMALY_LIFECYCLE_TRANSITION = "unusual_lifecycle_transition"

ANOMALY_TYPES = [
    ANOMALY_TREND_SPIKE,
    ANOMALY_SCORE_COLLAPSE,
    ANOMALY_COMPETITION_SURGE,
    ANOMALY_DEMAND_BREAKDOWN,
    ANOMALY_LIFECYCLE_TRANSITION,
]

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _alert(
    target_entity: str,
    anomaly_type: str,
    severity: str,
    supporting_signal_summary: Dict[str, Any],
    alert_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "alert_id": (alert_id or str(uuid.uuid4())[:12]),
        "target_entity": (target_entity or "").strip() or "unknown",
        "anomaly_type": anomaly_type,
        "severity": severity,
        "supporting_signal_summary": dict(supporting_signal_summary or {}),
        "timestamp": _now_iso(),
    }


def _severity_from_drift(drift: Dict[str, Any]) -> str:
    d = (drift.get("severity") or "").strip().lower()
    if d == "high":
        return SEVERITY_HIGH
    if d == "medium":
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def detect_anomalies_from_drift(
    drift_reports: Sequence[Dict[str, Any]],
    target_entity: str = "",
) -> List[Dict[str, Any]]:
    """
    Convert signal drift detector outputs into anomaly alerts.
    Collapse -> opportunity_score_collapse; Spike -> sudden_trend_spike; Sudden_shift -> trend spike or collapse by direction.
    """
    alerts: List[Dict[str, Any]] = []
    target = (target_entity or "").strip() or "unknown"
    for d in drift_reports or []:
        drift_type = (d.get("drift_type") or "").strip().lower()
        signal_type = (d.get("signal_type") or "").strip()
        severity = _severity_from_drift(d)
        supporting = {"drift_type": drift_type, "signal_type": signal_type, "drift_report": d}
        if drift_type == "collapse":
            anomaly_type = ANOMALY_SCORE_COLLAPSE if "opportunity" in signal_type or "score" in signal_type else ANOMALY_DEMAND_BREAKDOWN if signal_type == "demand_score" else ANOMALY_SCORE_COLLAPSE
            if signal_type == "competition_score":
                anomaly_type = ANOMALY_COMPETITION_SURGE
            alerts.append(_alert(target, anomaly_type, SEVERITY_HIGH if severity == SEVERITY_LOW else severity, supporting))
        elif drift_type == "spike":
            if "trend" in signal_type:
                alerts.append(_alert(target, ANOMALY_TREND_SPIKE, severity, supporting))
            else:
                alerts.append(_alert(target, ANOMALY_TREND_SPIKE, severity, supporting))
        elif drift_type == "sudden_shift":
            ratio = d.get("ratio") or 0
            if isinstance(ratio, (int, float)) and ratio > 1:
                alerts.append(_alert(target, ANOMALY_TREND_SPIKE, severity, supporting))
            else:
                alerts.append(_alert(target, ANOMALY_SCORE_COLLAPSE, severity, supporting))
    return alerts


def detect_anomalies_from_lifecycle(
    lifecycle_output: Dict[str, Any],
    target_entity: str = "",
    previous_state: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Detect unusual lifecycle transitions. E.g. rising -> fading without maturing, or emerging -> weakening.
    """
    alerts: List[Dict[str, Any]] = []
    target = (target_entity or "").strip() or (lifecycle_output.get("opportunity_id") or "").strip() or "unknown"
    current = (lifecycle_output.get("lifecycle_state") or "").strip().lower()
    if not current:
        return []
    unusual_transitions = [
        ("rising", "fading"),
        ("accelerating", "weakening"),
        ("emerging", "fading"),
        ("maturing", "fading"),
        ("rising", "weakening"),
    ]
    if previous_state:
        prev = previous_state.strip().lower()
        if (prev, current) in unusual_transitions:
            severity = SEVERITY_HIGH if current == "fading" else SEVERITY_MEDIUM
            supporting = {
                "previous_state": prev,
                "current_state": current,
                "lifecycle_score": lifecycle_output.get("lifecycle_score"),
                "supporting_signal_summary": lifecycle_output.get("supporting_signal_summary"),
            }
            alerts.append(_alert(target, ANOMALY_LIFECYCLE_TRANSITION, severity, supporting))
    return alerts


def detect_demand_breakdown(
    current_demand: Optional[float],
    history_demand: Sequence[float],
    target_entity: str = "",
    collapse_threshold_ratio: float = 0.2,
) -> Optional[Dict[str, Any]]:
    """Flag demand breakdown when current demand is very low vs recent history."""
    if current_demand is None or not history_demand:
        return None
    try:
        cur = float(current_demand)
        recent = list(history_demand)[-10:]
        if not recent:
            return None
        max_d = max(float(x) for x in recent if x is not None)
        if max_d <= 0:
            return None
        if cur / max_d >= collapse_threshold_ratio:
            return None
        severity = SEVERITY_CRITICAL if cur / max_d < 0.05 else (SEVERITY_HIGH if cur / max_d < 0.15 else SEVERITY_MEDIUM)
        return _alert(
            (target_entity or "").strip() or "unknown",
            ANOMALY_DEMAND_BREAKDOWN,
            severity,
            {"current_demand": cur, "recent_max_demand": max_d, "ratio": round(cur / max_d, 2)},
        )
    except (TypeError, ValueError):
        return None


def detect_competition_surge(
    current_competition: Optional[float],
    history_competition: Sequence[float],
    target_entity: str = "",
    surge_ratio: float = 1.8,
) -> Optional[Dict[str, Any]]:
    """Flag competition surge when current competition is much higher than recent average."""
    if current_competition is None or not history_competition:
        return None
    try:
        cur = float(current_competition)
        recent = list(history_competition)[-5:]
        if not recent:
            return None
        avg = sum(float(x) for x in recent if x is not None) / len(recent)
        if avg <= 0:
            return None
        if cur / avg < surge_ratio:
            return None
        severity = SEVERITY_HIGH if cur / avg >= 2.5 else SEVERITY_MEDIUM
        return _alert(
            (target_entity or "").strip() or "unknown",
            ANOMALY_COMPETITION_SURGE,
            severity,
            {"current_competition": cur, "recent_avg_competition": round(avg, 2), "ratio": round(cur / avg, 2)},
        )
    except (TypeError, ValueError):
        return None


def get_anomaly_alerts(
    target_entity: str = "",
    drift_reports: Optional[Sequence[Dict[str, Any]]] = None,
    lifecycle_output: Optional[Dict[str, Any]] = None,
    previous_lifecycle_state: Optional[str] = None,
    demand_current: Optional[float] = None,
    demand_history: Optional[Sequence[float]] = None,
    competition_current: Optional[float] = None,
    competition_history: Optional[Sequence[float]] = None,
) -> List[Dict[str, Any]]:
    """
    Aggregate anomaly detection from drift, lifecycle, demand, and competition. Returns list of anomaly alerts.
    """
    out: List[Dict[str, Any]] = []
    target = (target_entity or "").strip() or (lifecycle_output or {}).get("opportunity_id") or "unknown"
    if drift_reports:
        out.extend(detect_anomalies_from_drift(drift_reports, target_entity=target))
    if lifecycle_output:
        out.extend(detect_anomalies_from_lifecycle(lifecycle_output, target_entity=target, previous_state=previous_lifecycle_state))
    if demand_current is not None and demand_history:
        a = detect_demand_breakdown(demand_current, demand_history, target_entity=target)
        if a:
            out.append(a)
    if competition_current is not None and competition_history:
        a = detect_competition_surge(competition_current, competition_history, target_entity=target)
        if a:
            out.append(a)
    return out


def to_prioritized_alert(anomaly_alert: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert anomaly alert to prioritized alert format for alert prioritization and dashboard.
    Returns result of prioritize_alert(alert, SOURCE_TREND) so it can be merged with get_prioritized_alerts.
    """
    try:
        from amazon_research.discovery.alert_prioritization import prioritize_alert, SOURCE_TREND
        payload = {
            "id": anomaly_alert.get("alert_id"),
            "alert_id": anomaly_alert.get("alert_id"),
            "target_entity": anomaly_alert.get("target_entity"),
            "alert_type": anomaly_alert.get("anomaly_type"),
            "severity": anomaly_alert.get("severity"),
            "triggering_signals": anomaly_alert.get("supporting_signal_summary"),
            "recorded_at": anomaly_alert.get("timestamp"),
            "timestamp": anomaly_alert.get("timestamp"),
        }
        return prioritize_alert(payload, SOURCE_TREND, alert_id=anomaly_alert.get("alert_id"))
    except Exception as e:
        logger.debug("to_prioritized_alert: %s", e)
        return {
            "alert_id": anomaly_alert.get("alert_id"),
            "alert_source": "anomaly",
            "priority_score": 60.0,
            "priority_label": "medium",
            "signal_summary": anomaly_alert.get("supporting_signal_summary"),
            "timestamp": anomaly_alert.get("timestamp"),
        }


def get_anomaly_alerts_for_opportunity(
    opportunity_ref: str,
    memory_record: Optional[Dict[str, Any]] = None,
    lifecycle_output: Optional[Dict[str, Any]] = None,
    drift_reports: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate anomaly alerts for one opportunity using memory, lifecycle, and optional drift.
    If drift_reports not provided, uses signal drift detector when score_history is available.
    """
    ref = (opportunity_ref or "").strip()
    if not ref:
        return []
    mem = memory_record
    if mem is None:
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
        except Exception as e:
            logger.debug("get_anomaly_alerts_for_opportunity get_opportunity_memory: %s", e)
    life = lifecycle_output
    if life is None and mem:
        try:
            from amazon_research.discovery.opportunity_lifecycle_engine import get_lifecycle_state
            life = get_lifecycle_state(ref, memory_record=mem)
        except Exception as e:
            logger.debug("get_anomaly_alerts_for_opportunity get_lifecycle_state: %s", e)
    drifts = drift_reports
    if drifts is None and mem:
        try:
            from amazon_research.monitoring.signal_drift_detector import run_drift_checks
            sh = (mem.get("score_history") or [])[-10:]
            if len(sh) >= 2:
                hist = [{"opportunity_index": p.get("score") if isinstance(p, dict) else p} for p in sh[:-1]]
                cur = sh[-1]
                cur_ctx = {"opportunity_index": cur.get("score") if isinstance(cur, dict) else cur}
                r = run_drift_checks(current_context=cur_ctx, history_contexts=hist, target_id=ref)
                drifts = r.get("drifts") or []
        except Exception as e:
            logger.debug("get_anomaly_alerts_for_opportunity run_drift_checks: %s", e)
            drifts = []
    demand_hist: Optional[List[float]] = None
    comp_hist: Optional[List[float]] = None
    if mem:
        sh = mem.get("score_history") or []
        if isinstance(sh, list):
            demand_hist = [float(m.get("demand_score")) for m in sh if isinstance(m, dict) and m.get("demand_score") is not None]
            comp_hist = [float(m.get("competition_score")) for m in sh if isinstance(m, dict) and m.get("competition_score") is not None]
        if not demand_hist:
            demand_hist = None
        if not comp_hist:
            comp_hist = None
    return get_anomaly_alerts(
        target_entity=ref,
        drift_reports=drifts or [],
        lifecycle_output=life,
        demand_current=mem.get("demand_score") if mem else None,
        demand_history=demand_hist,
        competition_current=mem.get("competition_score") if mem else None,
        competition_history=comp_hist,
    )
