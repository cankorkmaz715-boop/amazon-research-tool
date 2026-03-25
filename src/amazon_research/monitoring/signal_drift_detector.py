"""
Step 171: Signal drift detector – detect significant changes in market signals over time.
Monitors demand_score, competition_score, trend_score, opportunity_index, niche_score.
Detection: gradual drift, sudden shift, signal collapse, signal spike.
Uses moving average comparison, deviation threshold, rate-of-change. Lightweight, rule-based.
Integrates with scoring engine, trend engine, opportunity index, niche analysis (consumes their outputs).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.signal_drift_detector")

# Signal types to monitor
SIGNAL_DEMAND = "demand_score"
SIGNAL_COMPETITION = "competition_score"
SIGNAL_TREND = "trend_score"
SIGNAL_OPPORTUNITY_INDEX = "opportunity_index"
SIGNAL_NICHE = "niche_score"

SIGNAL_TYPES = [
    SIGNAL_DEMAND,
    SIGNAL_COMPETITION,
    SIGNAL_TREND,
    SIGNAL_OPPORTUNITY_INDEX,
    SIGNAL_NICHE,
]

# Drift types
DRIFT_GRADUAL = "gradual"
DRIFT_SUDDEN_SHIFT = "sudden_shift"
DRIFT_COLLAPSE = "collapse"
DRIFT_SPIKE = "spike"

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

# Thresholds (tunable)
MOVING_AVG_WINDOW = 5
DEVIATION_THRESHOLD_HIGH = 0.5   # 50% deviation from MA -> high
DEVIATION_THRESHOLD_MED = 0.25   # 25% -> medium
COLLAPSE_RATIO = 0.1             # current < 10% of recent max -> collapse
SPIKE_RATIO = 2.0                # current > 2x recent avg -> spike
SUDDEN_SHIFT_RATIO = 1.8         # current/prev or prev/current > 1.8 -> sudden shift
GRADUAL_SLOPE_MIN_POINTS = 3     # min points to detect gradual trend


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _report(
    signal_type: str,
    target_id: str,
    drift_type: str,
    severity: str,
    **extra: Any,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "signal_type": signal_type,
        "target_id": (target_id or "").strip() or "unknown",
        "drift_type": drift_type,
        "severity": severity,
        "timestamp": _now_iso(),
    }
    out.update(extra)
    return out


def _to_values(history: Sequence[Any], value_key: str = "value") -> List[float]:
    """Extract numeric values from history (list of numbers or list of dicts with value_key)."""
    out: List[float] = []
    for item in history:
        if item is None:
            continue
        if isinstance(item, (int, float)):
            out.append(float(item))
        elif isinstance(item, dict):
            v = item.get(value_key) or item.get("demand_score") or item.get("competition_score") or item.get("trend_score") or item.get("opportunity_index") or item.get("niche_score")
            if v is not None:
                try:
                    out.append(float(v))
                except (TypeError, ValueError):
                    pass
    return out


def _moving_avg(values: Sequence[float], window: int) -> Optional[float]:
    if not values or window <= 0:
        return None
    window = min(window, len(values))
    recent = values[-window:]
    return sum(recent) / len(recent)


def _rate_of_change(current: float, previous: float) -> Optional[float]:
    if previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous)


def detect_collapse(
    signal_type: str,
    current: float,
    history: Sequence[float],
    target_id: str = "",
    collapse_ratio: float = COLLAPSE_RATIO,
) -> Optional[Dict[str, Any]]:
    """
    Detect signal collapse: current falls to near zero relative to recent max.
    """
    if not history:
        return None
    recent = history[-MOVING_AVG_WINDOW:] if len(history) >= MOVING_AVG_WINDOW else history
    max_val = max(recent) if recent else current
    if max_val <= 0:
        return None
    ratio = current / max_val
    if ratio > collapse_ratio:
        return None
    severity = SEVERITY_HIGH if ratio < 0.02 else (SEVERITY_MEDIUM if ratio < 0.05 else SEVERITY_LOW)
    return _report(signal_type, target_id, DRIFT_COLLAPSE, severity, current_value=current, recent_max=max_val)


def detect_spike(
    signal_type: str,
    current: float,
    history: Sequence[float],
    target_id: str = "",
    spike_ratio: float = SPIKE_RATIO,
) -> Optional[Dict[str, Any]]:
    """
    Detect signal spike: current suddenly much higher than recent average.
    """
    if not history:
        return None
    ma = _moving_avg(history, MOVING_AVG_WINDOW)
    if ma is None or ma <= 0:
        return None
    ratio = current / ma
    if ratio < spike_ratio:
        return None
    severity = SEVERITY_HIGH if ratio >= 4.0 else (SEVERITY_MEDIUM if ratio >= 2.5 else SEVERITY_LOW)
    return _report(signal_type, target_id, DRIFT_SPIKE, severity, current_value=current, recent_avg=ma)


def detect_sudden_shift(
    signal_type: str,
    current: float,
    history: Sequence[float],
    target_id: str = "",
    shift_ratio: float = SUDDEN_SHIFT_RATIO,
) -> Optional[Dict[str, Any]]:
    """
    Detect sudden shift: current vs previous step changes sharply (e.g. doubles).
    """
    if len(history) < 2:
        return None
    prev = history[-1]
    if prev is None or prev == 0:
        return None
    ratio = current / prev
    if ratio <= shift_ratio and (1.0 / ratio) <= shift_ratio:
        return None
    severity = SEVERITY_HIGH if ratio >= 3.0 or ratio <= 1.0 / 3.0 else (SEVERITY_MEDIUM if ratio >= 2.0 or ratio <= 0.5 else SEVERITY_LOW)
    return _report(signal_type, target_id, DRIFT_SUDDEN_SHIFT, severity, current_value=current, previous_value=prev, ratio=round(ratio, 2))


def detect_gradual_drift(
    signal_type: str,
    history: Sequence[float],
    target_id: str = "",
    window: int = MOVING_AVG_WINDOW,
    deviation_medium: float = DEVIATION_THRESHOLD_MED,
    deviation_high: float = DEVIATION_THRESHOLD_HIGH,
) -> Optional[Dict[str, Any]]:
    """
    Detect gradual drift: recent trend consistently up or down vs earlier average.
    Compare first half vs second half of window (or recent vs older MA).
    """
    if len(history) < GRADUAL_SLOPE_MIN_POINTS or window < 2:
        return None
    # Use half-window for short series so we have both "older" and "recent" segments
    n = min(max(1, len(history) // 2), window)
    recent = history[-n:]
    older = history[: max(1, len(history) - n)]
    if len(older) < 1 or len(recent) < 1:
        return None
    ma_older = sum(older) / len(older)
    ma_recent = sum(recent) / len(recent)
    if ma_older == 0:
        return None
    change = (ma_recent - ma_older) / abs(ma_older)
    if abs(change) < deviation_medium:
        return None
    severity = SEVERITY_HIGH if abs(change) >= deviation_high else SEVERITY_MEDIUM
    return _report(
        signal_type, target_id, DRIFT_GRADUAL, severity,
        recent_avg=round(ma_recent, 2), older_avg=round(ma_older, 2), change_pct=round(change * 100, 1),
    )


def detect_drift(
    signal_type: str,
    current_value: float,
    history: Sequence[Any],
    target_id: str = "",
    value_key: str = "value",
) -> List[Dict[str, Any]]:
    """
    Run all drift checks for one signal. Returns list of drift reports (may be empty).
    history: list of past values (floats or dicts with value_key or signal keys).
    """
    values = _to_values(history, value_key=value_key)
    if current_value is not None:
        try:
            values = values + [float(current_value)]
        except (TypeError, ValueError):
            pass
    if len(values) < 2:
        return []
    current = values[-1]
    reports: List[Dict[str, Any]] = []
    # Collapse
    r = detect_collapse(signal_type, current, values[:-1], target_id=target_id)
    if r:
        reports.append(r)
    # Spike
    r = detect_spike(signal_type, current, values[:-1], target_id=target_id)
    if r:
        reports.append(r)
    # Sudden shift
    r = detect_sudden_shift(signal_type, current, values[:-1], target_id=target_id)
    if r:
        reports.append(r)
    # Gradual
    r = detect_gradual_drift(signal_type, values, target_id=target_id)
    if r:
        reports.append(r)
    return reports


def detect_drift_from_context(
    current_context: Dict[str, Any],
    history_contexts: Sequence[Dict[str, Any]],
    target_id: str = "",
) -> List[Dict[str, Any]]:
    """
    Run drift detection for all monitored signal types from context dicts.
    current_context and each history item can have demand_score, competition_score, trend_score, opportunity_index, niche_score.
    """
    all_reports: List[Dict[str, Any]] = []
    for sig in SIGNAL_TYPES:
        key = sig
        cur = current_context.get(key)
        if cur is None and sig == SIGNAL_OPPORTUNITY_INDEX:
            cur = current_context.get("opportunity_score")
        hist_flat: List[float] = []
        for h in history_contexts:
            v = h.get(key)
            if v is None and sig == SIGNAL_OPPORTUNITY_INDEX:
                v = h.get("opportunity_score")
            if v is not None:
                try:
                    hist_flat.append(float(v))
                except (TypeError, ValueError):
                    pass
        if cur is not None:
            try:
                cur_f = float(cur)
                reports = detect_drift(signal_type=sig, current_value=cur_f, history=hist_flat, target_id=target_id)
                all_reports.extend(reports)
            except (TypeError, ValueError):
                pass
    return all_reports


def run_drift_checks(
    current_context: Optional[Dict[str, Any]] = None,
    history_contexts: Optional[Sequence[Dict[str, Any]]] = None,
    target_id: str = "",
) -> Dict[str, Any]:
    """
    Run drift detection across signals. If current_context/history not provided, returns empty list.
    Returns { "drifts": [...], "target_id": "...", "timestamp": "..." }.
    """
    ts = _now_iso()
    if not current_context or not history_contexts:
        return {"drifts": [], "target_id": (target_id or "").strip() or "unknown", "timestamp": ts}
    drifts = detect_drift_from_context(current_context, list(history_contexts), target_id=target_id)
    return {"drifts": drifts, "target_id": (target_id or "").strip() or "unknown", "timestamp": ts}
