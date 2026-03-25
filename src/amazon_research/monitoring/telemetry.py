"""
Cost and bandwidth telemetry. Step 48 – lightweight, internal-first. No billing integration.
Tracks approximate bandwidth (pages, estimated bytes) and cost-oriented hints by flow.
"""
import threading
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.telemetry")

# Default estimated bytes per page (for proxy/bandwidth summary)
_DEFAULT_BYTES_PER_PAGE = 500_000

_lock = threading.Lock()
_bandwidth: Dict[str, Dict[str, int]] = {}  # flow -> { "pages": int, "estimated_bytes": int }
_cost_hints: Dict[str, Dict[str, Any]] = {}  # flow -> { key: value }


def record_bandwidth(flow: str, pages: int = 1, estimated_bytes: Optional[int] = None) -> None:
    """Record approximate bandwidth for a flow (discovery, refresh, related_sponsored, graph_expansion)."""
    flow = (flow or "unknown").strip()
    if not flow:
        return
    with _lock:
        if flow not in _bandwidth:
            _bandwidth[flow] = {"pages": 0, "estimated_bytes": 0}
        _bandwidth[flow]["pages"] += max(0, pages)
        add_bytes = estimated_bytes if estimated_bytes is not None else max(0, pages) * _DEFAULT_BYTES_PER_PAGE
        _bandwidth[flow]["estimated_bytes"] += add_bytes


def record_cost_hint(flow: str, key: str, value: Any) -> None:
    """Record a cost-oriented hint (e.g. proxy_sessions, candidates_count) for summarization."""
    flow = (flow or "unknown").strip()
    if not flow or not key:
        return
    with _lock:
        if flow not in _cost_hints:
            _cost_hints[flow] = {}
        if key not in _cost_hints[flow]:
            _cost_hints[flow][key] = 0
        try:
            _cost_hints[flow][key] += float(value)
        except (TypeError, ValueError):
            _cost_hints[flow][key] = value


def get_bandwidth_summary() -> Dict[str, Any]:
    """Return bandwidth summary: by_flow, total_pages, total_estimated_bytes."""
    with _lock:
        by_flow = {k: dict(v) for k, v in _bandwidth.items()}
        total_pages = sum(b["pages"] for b in _bandwidth.values())
        total_bytes = sum(b["estimated_bytes"] for b in _bandwidth.values())
    return {
        "by_flow": by_flow,
        "total_pages": total_pages,
        "total_estimated_bytes": total_bytes,
        "total_estimated_mb": round(total_bytes / (1024 * 1024), 2),
    }


def get_cost_summary() -> Dict[str, Any]:
    """Return cost-oriented summary (hints by flow and aggregated)."""
    with _lock:
        by_flow = {k: dict(v) for k, v in _cost_hints.items()}
    return {"by_flow": by_flow}


def get_flow_attribution() -> List[str]:
    """Return list of flows that have recorded bandwidth or cost hints."""
    with _lock:
        flows = set(_bandwidth.keys()) | set(_cost_hints.keys())
    return sorted(flows)


def get_telemetry_summary() -> Dict[str, Any]:
    """Return full telemetry summary: bandwidth, cost, flow attribution. Safe and compact."""
    return {
        "bandwidth": get_bandwidth_summary(),
        "cost": get_cost_summary(),
        "flows": get_flow_attribution(),
    }


def reset_telemetry() -> None:
    """Reset all counters (e.g. for tests or new run)."""
    with _lock:
        _bandwidth.clear()
        _cost_hints.clear()
