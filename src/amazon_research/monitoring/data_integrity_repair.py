"""
Step 166: Data integrity repair layer – attempt to fix issues detected by the data quality guard.
Handles missing metrics, partial scrape, timeseries gaps, signal reconstruction, anomaly smoothing.
Conservative and safe; does not rewrite crawler or scoring engine. Integrates with data quality guard,
scraper reliability, recovery/retry orchestrator.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.data_integrity_repair")

REPAIR_FIXED = "FIXED"
REPAIR_SKIPPED = "SKIPPED"
REPAIR_FAILED = "FAILED"

ISSUE_MISSING_DATA = "missing_data"
ISSUE_PARTIAL_SCRAPE = "partial_scrape"
ISSUE_TIMESERIES_GAP = "timeseries_gap"
ISSUE_MISSING_SIGNALS = "missing_signals"
ISSUE_ANOMALY = "single_snapshot_anomaly"


def _report(
    repair_status: str,
    issue_type: str,
    repair_method: str,
    target_id: str,
    **extra: Any,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "repair_status": repair_status,
        "issue_type": issue_type,
        "repair_method": repair_method,
        "target_id": (target_id or "").strip() or "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    out.update(extra)
    return out


def missing_data_repair(
    record: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    target_id: str = "",
) -> Dict[str, Any]:
    """
    Attempt re-fetch of missing fields. Conservative: we do not call the crawler; we recommend re-fetch
    and return SKIPPED. Pipeline can use this to requeue a refresh job.
    """
    tid = (target_id or "").strip() or "unknown"
    if not record and not context:
        return _report(REPAIR_SKIPPED, ISSUE_MISSING_DATA, "recommend_refetch", tid)
    # Cannot re-fetch from this layer; suggest downstream to requeue
    return _report(REPAIR_SKIPPED, ISSUE_MISSING_DATA, "recommend_refetch", tid)


def partial_scrape_repair(
    target_id: str,
    job_type: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Requeue scrape job for partial scrape. If payload and enqueue_job are available, enqueue and return FIXED.
    Otherwise return SKIPPED or FAILED.
    """
    tid = (target_id or "").strip() or "unknown"
    if not payload or not job_type:
        return _report(REPAIR_SKIPPED, ISSUE_PARTIAL_SCRAPE, "requeue_skipped_no_payload", tid)
    try:
        from amazon_research.db import enqueue_job
        jid = enqueue_job(job_type=job_type, workspace_id=workspace_id, payload=payload)
        if jid:
            return _report(REPAIR_FIXED, ISSUE_PARTIAL_SCRAPE, "requeue_scrape_job", tid, job_id=jid)
        return _report(REPAIR_FAILED, ISSUE_PARTIAL_SCRAPE, "requeue_returned_none", tid)
    except Exception as e:
        logger.debug("partial_scrape_repair enqueue_job: %s", e)
        return _report(REPAIR_FAILED, ISSUE_PARTIAL_SCRAPE, "requeue_failed", tid, error=str(e)[:200])


def _parse_ts(v: Any) -> Optional[float]:
    if v is None:
        return None
    from datetime import datetime
    if hasattr(v, "timestamp"):
        return v.timestamp()
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return None
    return None


def timeseries_gap_repair(
    history: Sequence[Dict[str, Any]],
    date_key: str = "recorded_at",
    value_key: str = "bsr",
    target_id: str = "",
) -> Dict[str, Any]:
    """
    Interpolate or request additional snapshots for timeseries gaps. Conservative: interpolate missing
    value at mid-gap using neighbors when exactly one point is missing between two valid points.
    Returns repair report and optionally repaired_series.
    """
    tid = (target_id or "").strip() or "unknown"
    if not history or len(history) < 2:
        return _report(REPAIR_SKIPPED, ISSUE_TIMESERIES_GAP, "insufficient_points", tid)
    repaired: List[Dict[str, Any]] = []
    fixed_count = 0
    for i, entry in enumerate(history):
        repaired.append(dict(entry))
        val = entry.get(value_key)
        if val is not None:
            continue
        # Missing value: try linear interpolation from prev/next
        prev_val = history[i - 1].get(value_key) if i > 0 else None
        next_val = history[i + 1].get(value_key) if i + 1 < len(history) else None
        if prev_val is not None and next_val is not None:
            try:
                interp = (float(prev_val) + float(next_val)) / 2.0
                repaired[-1][value_key] = round(interp, 2)
                fixed_count += 1
            except (TypeError, ValueError):
                pass
    if fixed_count > 0:
        return _report(REPAIR_FIXED, ISSUE_TIMESERIES_GAP, "interpolate_gap", tid, repaired_series=repaired, interpolated_count=fixed_count)
    return _report(REPAIR_SKIPPED, ISSUE_TIMESERIES_GAP, "no_gaps_interpolated", tid)


def signal_reconstruction(
    context: Optional[Dict[str, Any]] = None,
    target_id: str = "",
) -> Dict[str, Any]:
    """
    Recompute signal if raw inputs exist. If demand_score/competition_score/trend_score are missing
    but we have raw inputs (e.g. demand_raw, competition_raw), derive and return FIXED with reconstructed context.
    """
    tid = (target_id or "").strip() or "unknown"
    if not context:
        return _report(REPAIR_SKIPPED, ISSUE_MISSING_SIGNALS, "no_context", tid)
    out = dict(context)
    fixed = False
    if out.get("demand_score") is None and out.get("demand") is None and out.get("demand_raw") is not None:
        try:
            out["demand_score"] = float(out["demand_raw"])
            fixed = True
        except (TypeError, ValueError):
            pass
    if out.get("competition_score") is None and out.get("competition") is None and out.get("competition_raw") is not None:
        try:
            out["competition_score"] = float(out["competition_raw"])
            fixed = True
        except (TypeError, ValueError):
            pass
    if out.get("trend_score") is None and out.get("trend") is None and out.get("trend_raw") is not None:
        try:
            out["trend_score"] = float(out["trend_raw"])
            fixed = True
        except (TypeError, ValueError):
            pass
    if fixed:
        return _report(REPAIR_FIXED, ISSUE_MISSING_SIGNALS, "recompute_from_raw", tid, reconstructed_context=out)
    return _report(REPAIR_SKIPPED, ISSUE_MISSING_SIGNALS, "no_raw_inputs", tid)


def anomaly_smoothing(
    series: Sequence[Dict[str, Any]],
    value_key: str = "bsr",
    spike_ratio_threshold: float = 50.0,
    target_id: str = "",
) -> Dict[str, Any]:
    """
    Suppress extreme single-point spikes. Replace value with average of neighbors when it deviates
    from both neighbors by more than spike_ratio_threshold (ratio). Conservative: only smooth clear spikes.
    """
    tid = (target_id or "").strip() or "unknown"
    if not series or len(series) < 3:
        return _report(REPAIR_SKIPPED, ISSUE_ANOMALY, "insufficient_points", tid)
    smoothed: List[Dict[str, Any]] = []
    fixed_count = 0
    for i, entry in enumerate(series):
        row = dict(entry)
        val = entry.get(value_key)
        if val is None or i == 0 or i == len(series) - 1:
            smoothed.append(row)
            continue
        try:
            cur = float(val)
            prev = float(series[i - 1].get(value_key))
            nxt = float(series[i + 1].get(value_key))
        except (TypeError, ValueError):
            smoothed.append(row)
            continue
        if prev == 0 or nxt == 0:
            smoothed.append(row)
            continue
        # Spike: cur >> prev and cur >> nxt, or cur << prev and cur << nxt
        ratio_prev = cur / prev if prev else 0
        ratio_next = cur / nxt if nxt else 0
        if ratio_prev >= spike_ratio_threshold and ratio_next >= spike_ratio_threshold:
            row[value_key] = round((prev + nxt) / 2.0, 2)
            fixed_count += 1
        elif ratio_prev <= 1.0 / spike_ratio_threshold and ratio_next <= 1.0 / spike_ratio_threshold:
            row[value_key] = round((prev + nxt) / 2.0, 2)
            fixed_count += 1
        smoothed.append(row)
    if fixed_count > 0:
        return _report(REPAIR_FIXED, ISSUE_ANOMALY, "smooth_spike", tid, smoothed_series=smoothed, smoothed_count=fixed_count)
    return _report(REPAIR_SKIPPED, ISSUE_ANOMALY, "no_spikes_detected", tid)


def run_repairs_for_quality_issues(
    issues: List[Dict[str, Any]],
    record: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    target_id: str = "",
) -> List[Dict[str, Any]]:
    """
    Given a list of issues from the data quality guard, run applicable repairs and return list of repair reports.
    Conservative: only runs repairs that match issue check names and have required data.
    """
    reports: List[Dict[str, Any]] = []
    tid = (target_id or "").strip() or "unknown"
    for issue in issues:
        check = (issue.get("check") or "").strip()
        if check == "missing_data":
            reports.append(missing_data_repair(record=record, context=context, target_id=tid))
        elif check == "signal_presence" and context is not None:
            reports.append(signal_reconstruction(context=context, target_id=tid))
        elif check == "history_continuity" and history:
            reports.append(timeseries_gap_repair(history=history, target_id=tid))
        elif check == "anomaly_detection" and history:
            reports.append(anomaly_smoothing(series=history, target_id=tid))
    return reports
