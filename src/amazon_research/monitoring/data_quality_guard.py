"""
Step 162: Data quality guard – validate product/ASIN data before it propagates into scoring or analytics.
Detects incomplete, corrupted, or abnormal data. Does not stop pipeline; only flags issues. Lightweight.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.data_quality_guard")

QUALITY_OK = "OK"
QUALITY_WARNING = "WARNING"
QUALITY_FAIL = "FAIL"
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

# Required fields for product/ASIN metrics (missing = issue)
REQUIRED_PRODUCT_FIELDS = ["asin", "title"]
REQUIRED_METRIC_FIELDS = ["price", "rating", "review_count"]
REQUIRED_SIGNALS = ["demand", "competition", "trend"]


def _issue(check: str, message: str, severity: str = SEVERITY_MEDIUM) -> Dict[str, Any]:
    return {"check": check, "message": message, "severity": severity}


def _parse_ts(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def missing_data_check(
    record: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Detect if required fields are empty or null.
    record: product/ASIN metrics (asin, title, price, rating, review_count).
    context: scoring context (demand_score, competition_score, trend_score or trend).
    """
    issues: List[Dict[str, Any]] = []
    if record is not None:
        for key in REQUIRED_PRODUCT_FIELDS:
            val = record.get(key)
            if val is None or (isinstance(val, str) and not val.strip()):
                issues.append(_issue("missing_data", f"required field '{key}' empty or null", SEVERITY_MEDIUM))
        # Metric fields: at least one should be present for meaningful data
        has_metric = any(record.get(k) is not None for k in REQUIRED_METRIC_FIELDS)
        if not has_metric and (record.get("price") is None and record.get("rating") is None and record.get("review_count") is None):
            issues.append(_issue("missing_data", "all of price, rating, review_count are null", SEVERITY_LOW))
    if context is not None:
        demand = context.get("demand_score") if context.get("demand_score") is not None else context.get("demand")
        comp = context.get("competition_score") if context.get("competition_score") is not None else context.get("competition")
        trend = context.get("trend_score") if context.get("trend_score") is not None else context.get("trend")
        if demand is None:
            issues.append(_issue("missing_data", "demand signal missing", SEVERITY_MEDIUM))
        if comp is None:
            issues.append(_issue("missing_data", "competition signal missing", SEVERITY_MEDIUM))
        if trend is None:
            issues.append(_issue("missing_data", "trend signal missing", SEVERITY_LOW))
    return issues


def numeric_range_check(record: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Ensure values fall within expected ranges: price > 0, review_count >= 0, rating between 0 and 5.
    """
    issues: List[Dict[str, Any]] = []
    if record is None:
        return issues
    price = record.get("price")
    if price is not None:
        try:
            p = float(price)
            if p <= 0:
                issues.append(_issue("numeric_range", "price must be > 0", SEVERITY_HIGH))
        except (TypeError, ValueError):
            issues.append(_issue("numeric_range", "price is not a valid number", SEVERITY_HIGH))
    review_count = record.get("review_count")
    if review_count is not None:
        try:
            r = int(review_count)
            if r < 0:
                issues.append(_issue("numeric_range", "review_count must be >= 0", SEVERITY_MEDIUM))
        except (TypeError, ValueError):
            issues.append(_issue("numeric_range", "review_count is not a valid integer", SEVERITY_MEDIUM))
    rating = record.get("rating")
    if rating is not None:
        try:
            r = float(rating)
            if r < 0 or r > 5:
                issues.append(_issue("numeric_range", "rating must be between 0 and 5", SEVERITY_HIGH))
        except (TypeError, ValueError):
            issues.append(_issue("numeric_range", "rating is not a valid number", SEVERITY_HIGH))
    return issues


def history_continuity_check(
    history: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    date_key: str = "recorded_at",
    max_gap_days: float = 7.0,
) -> List[Dict[str, Any]]:
    """
    Detect large gaps in time-series data (BSR or price history).
    history: list of dicts with a datetime field (recorded_at or similar).
    """
    issues: List[Dict[str, Any]] = []
    if not history or len(history) < 2:
        return issues
    prev_ts: Optional[datetime] = None
    for i, entry in enumerate(history):
        ts = _parse_ts(entry.get(date_key))
        if ts is None:
            continue
        if prev_ts is not None:
            delta = (ts - prev_ts).total_seconds() / (24 * 3600)
            if delta > max_gap_days:
                issues.append(_issue("history_continuity", f"gap of {delta:.0f} days at index {i} (>{max_gap_days} days)", SEVERITY_MEDIUM))
        prev_ts = ts
    return issues


def signal_presence_check(context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Verify required signals exist before scoring: demand, competition, trend.
    """
    issues: List[Dict[str, Any]] = []
    if context is None:
        issues.append(_issue("signal_presence", "no context provided", SEVERITY_MEDIUM))
        return issues
    demand = context.get("demand_score") is not None or context.get("demand") is not None
    comp = context.get("competition_score") is not None or context.get("competition") is not None
    trend = context.get("trend_score") is not None or context.get("trend") is not None
    if not demand:
        issues.append(_issue("signal_presence", "demand signal missing", SEVERITY_HIGH))
    if not comp:
        issues.append(_issue("signal_presence", "competition signal missing", SEVERITY_HIGH))
    if not trend:
        issues.append(_issue("signal_presence", "trend signal missing", SEVERITY_MEDIUM))
    return issues


def anomaly_detection_check(
    history: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    value_key: str = "bsr",
    spike_ratio_threshold: float = 100.0,
) -> List[Dict[str, Any]]:
    """
    Detect abnormal spikes in values (e.g. BSR jumping 500000 → 50 in one snapshot).
    Flags when consecutive values change by more than spike_ratio_threshold (e.g. 100x).
    """
    issues: List[Dict[str, Any]] = []
    if not history or len(history) < 2:
        return issues
    prev_val: Optional[float] = None
    for i, entry in enumerate(history):
        v = entry.get(value_key)
        if v is None:
            continue
        try:
            cur = float(v)
        except (TypeError, ValueError):
            continue
        if prev_val is not None and prev_val != 0:
            ratio = cur / prev_val
            # Spike up: ratio >= threshold. Spike down (e.g. BSR 500000 -> 50): ratio <= 1/threshold
            if ratio >= spike_ratio_threshold or (0 < ratio <= 1.0 / spike_ratio_threshold):
                issues.append(_issue("anomaly_detection", f"spike at index {i}: {prev_val} -> {cur} (ratio {ratio:.2g})", SEVERITY_HIGH))
        prev_val = cur
    return issues


def run_all_checks(
    record: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    history_date_key: str = "recorded_at",
    history_value_key: str = "bsr",
) -> Dict[str, Any]:
    """
    Run all data quality checks. Returns { "data_quality": "OK"|"WARNING"|"FAIL", "issues": [...] }.
    Does not stop pipeline execution; only flags issues.
    """
    issues: List[Dict[str, Any]] = []
    issues.extend(missing_data_check(record=record, context=context))
    issues.extend(numeric_range_check(record=record))
    issues.extend(history_continuity_check(history=history, date_key=history_date_key))
    issues.extend(signal_presence_check(context=context))
    issues.extend(anomaly_detection_check(history=history, value_key=history_value_key))

    if any(i.get("severity") == SEVERITY_HIGH for i in issues):
        data_quality = QUALITY_FAIL
    elif any(i.get("severity") == SEVERITY_MEDIUM for i in issues):
        data_quality = QUALITY_WARNING
    else:
        data_quality = QUALITY_OK

    return {"data_quality": data_quality, "issues": issues}
