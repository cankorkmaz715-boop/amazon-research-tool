"""
Step 195: Workspace intelligence metrics – observability for reads, cache, snapshots, refresh, fallbacks.
In-process counters; never crash request paths. Normalized summary for health and ops.
"""
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("workspace_intelligence.metrics")

_lock = threading.Lock()
_total_reads = 0
_cache_hits = 0
_cache_misses = 0
_snapshot_hits = 0
_compute_fallbacks = 0
_refresh_attempts = 0
_refresh_successes = 0
_refresh_failures = 0
_summary_build_duration_sum: float = 0.0
_summary_build_duration_count = 0
_refresh_duration_sum: float = 0.0
_refresh_duration_count = 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_read() -> None:
    """Record one workspace intelligence read (prefer_cached call)."""
    global _total_reads
    try:
        with _lock:
            _total_reads += 1
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_read failed: %s", e)


def record_cache_hit() -> None:
    """Record one cache hit."""
    global _cache_hits
    try:
        with _lock:
            _cache_hits += 1
        logger.debug("workspace_intelligence metrics cache hit recorded", extra={"cache_hit": True})
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_cache_hit failed: %s", e)


def record_cache_miss() -> None:
    """Record one cache miss (before persistence or compute fallback)."""
    global _cache_misses
    try:
        with _lock:
            _cache_misses += 1
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_cache_miss failed: %s", e)


def record_snapshot_hit() -> None:
    """Record one persistence snapshot hit."""
    global _snapshot_hits
    try:
        with _lock:
            _snapshot_hits += 1
        logger.debug("workspace_intelligence metrics snapshot hit recorded", extra={"snapshot_hit": True})
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_snapshot_hit failed: %s", e)


def record_compute_fallback() -> None:
    """Record one compute fallback."""
    global _compute_fallbacks
    try:
        with _lock:
            _compute_fallbacks += 1
        logger.debug("workspace_intelligence metrics compute fallback recorded", extra={"compute_fallback": True})
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_compute_fallback failed: %s", e)


def record_refresh_attempt() -> None:
    """Record one refresh attempt (per workspace in scheduler)."""
    global _refresh_attempts
    try:
        with _lock:
            _refresh_attempts += 1
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_refresh_attempt failed: %s", e)


def record_refresh_success(duration_seconds: Optional[float] = None) -> None:
    """Record one successful refresh; optional duration for averaging."""
    global _refresh_successes, _refresh_duration_sum, _refresh_duration_count
    try:
        with _lock:
            _refresh_successes += 1
            if duration_seconds is not None and duration_seconds >= 0:
                _refresh_duration_sum += float(duration_seconds)
                _refresh_duration_count += 1
        logger.debug("workspace_intelligence metrics refresh success recorded", extra={"duration_seconds": duration_seconds})
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_refresh_success failed: %s", e)


def record_refresh_failure(duration_seconds: Optional[float] = None) -> None:
    """Record one failed refresh; optional duration."""
    global _refresh_failures
    try:
        with _lock:
            _refresh_failures += 1
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_refresh_failure failed: %s", e)


def record_summary_build_duration(duration_seconds: float) -> None:
    """Record summary build duration for averaging (e.g. from get_workspace_intelligence_summary)."""
    global _summary_build_duration_sum, _summary_build_duration_count
    try:
        if duration_seconds is None or duration_seconds < 0:
            return
        with _lock:
            _summary_build_duration_sum += float(duration_seconds)
            _summary_build_duration_count += 1
    except Exception as e:
        logger.debug("workspace_intelligence metrics record_summary_build_duration failed: %s", e)


def get_workspace_intelligence_metrics_summary() -> Dict[str, Any]:
    """
    Return normalized metrics summary for workspace intelligence health.
    Safe defaults for all fields; never raises.
    """
    try:
        with _lock:
            total_reads = _total_reads
            cache_hits = _cache_hits
            cache_misses = _cache_misses
            snapshot_hits = _snapshot_hits
            compute_fallbacks = _compute_fallbacks
            refresh_attempts = _refresh_attempts
            refresh_successes = _refresh_successes
            refresh_failures = _refresh_failures
            build_sum = _summary_build_duration_sum
            build_count = _summary_build_duration_count
            ref_sum = _refresh_duration_sum
            ref_count = _refresh_duration_count
        avg_build = round(build_sum / build_count, 4) if build_count else None
        avg_refresh = round(ref_sum / ref_count, 4) if ref_count else None
        generated_at = _now_iso()
        logger.info(
            "workspace_intelligence metrics summary read",
            extra={"generated_at": generated_at, "total_reads": total_reads},
        )
        return {
            "generated_at": generated_at,
            "read_metrics": {"total_reads": total_reads},
            "cache_metrics": {"cache_hits": cache_hits, "cache_misses": cache_misses},
            "snapshot_metrics": {"snapshot_hits": snapshot_hits},
            "refresh_metrics": {
                "refresh_attempts": refresh_attempts,
                "refresh_successes": refresh_successes,
                "refresh_failures": refresh_failures,
            },
            "fallback_metrics": {"compute_fallbacks": compute_fallbacks},
            "performance_metrics": {
                "average_summary_build_duration_seconds": avg_build,
                "average_refresh_duration_seconds": avg_refresh,
                "summary_build_count": build_count,
                "refresh_duration_count": ref_count,
            },
        }
    except Exception as e:
        logger.warning("workspace_intelligence metrics summary failed: %s", e)
        return {
            "generated_at": _now_iso(),
            "read_metrics": {"total_reads": 0},
            "cache_metrics": {"cache_hits": 0, "cache_misses": 0},
            "snapshot_metrics": {"snapshot_hits": 0},
            "refresh_metrics": {"refresh_attempts": 0, "refresh_successes": 0, "refresh_failures": 0},
            "fallback_metrics": {"compute_fallbacks": 0},
            "performance_metrics": {
                "average_summary_build_duration_seconds": None,
                "average_refresh_duration_seconds": None,
                "summary_build_count": 0,
                "refresh_duration_count": 0,
            },
        }


def reset_workspace_intelligence_metrics_for_test_only() -> None:
    """
    Reset all workspace intelligence metrics counters. For tests only.
    Do not call in production; no side effects other than clearing in-memory counters.
    """
    global _total_reads, _cache_hits, _cache_misses, _snapshot_hits, _compute_fallbacks
    global _refresh_attempts, _refresh_successes, _refresh_failures
    global _summary_build_duration_sum, _summary_build_duration_count
    global _refresh_duration_sum, _refresh_duration_count
    try:
        with _lock:
            _total_reads = 0
            _cache_hits = 0
            _cache_misses = 0
            _snapshot_hits = 0
            _compute_fallbacks = 0
            _refresh_attempts = 0
            _refresh_successes = 0
            _refresh_failures = 0
            _summary_build_duration_sum = 0.0
            _summary_build_duration_count = 0
            _refresh_duration_sum = 0.0
            _refresh_duration_count = 0
    except Exception as e:
        logger.debug("workspace_intelligence metrics reset failed: %s", e)
