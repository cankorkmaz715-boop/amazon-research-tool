"""
Step 165: Recovery / Retry Orchestrator v2 – advanced recovery and retry orchestration on top of retry and scraper reliability.
Distinguishes failure categories; supports immediate/delayed retry, proxy rotation, target cooldown, skip/escalate.
Integrates with scraper reliability, worker queue, intelligent crawl scheduler, platform failure detector.
Lightweight, deterministic, rule-based. Extensible for adaptive policies.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.recovery_retry_orchestrator_v2")

# Failure categories
FAILURE_TEMPORARY_NETWORK = "temporary_network_failure"
FAILURE_PROXY = "proxy_failure"
FAILURE_BLOCKED_CAPTCHA = "blocked_response_captcha"
FAILURE_PARSER = "parser_failure"
FAILURE_REPEATED_TARGET = "repeated_target_failure"

# Recovery actions
ACTION_IMMEDIATE_RETRY = "immediate_retry"
ACTION_DELAYED_RETRY = "delayed_retry"
ACTION_PROXY_ROTATION_BEFORE_RETRY = "proxy_rotation_before_retry"
ACTION_TEMPORARY_TARGET_COOLDOWN = "temporary_target_cooldown"
ACTION_SKIP_ESCALATE = "skip_escalate_after_repeated"

# Per-target failure count (target_id -> list of timestamps, trim to last N)
_target_failures: Dict[str, List[float]] = {}
_MAX_FAILURES_TRACKED = 20
_REPEATED_THRESHOLD = 3
_COOLDOWN_SECONDS = 300  # 5 min default cooldown
_COOLDOWN_AFTER_REPEATED = 600  # 10 min after repeated


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_failure(
    raw_failure_type: Optional[str] = None,
    error_message: Optional[str] = None,
) -> str:
    """
    Classify failure into one of: temporary_network_failure, proxy_failure, blocked_response_captcha,
    parser_failure. Call record_target_failure + classify_failure to detect repeated_target_failure.
    """
    t = (raw_failure_type or "").strip().lower()
    msg = (error_message or "").strip().lower()
    if t in ("block", "blocked", "captcha") or "captcha" in msg or "blocked" in msg or "robot" in msg:
        return FAILURE_BLOCKED_CAPTCHA
    if t in ("proxy", "proxy_error", "connection_refused") or "proxy" in msg:
        return FAILURE_PROXY
    if t in ("parser", "parser_error", "parse") or "parse" in msg or "parser" in msg:
        return FAILURE_PARSER
    if t in ("timeout", "network", "connection", "connection_fail", "connection_failed") or "timeout" in msg or "connection" in msg:
        return FAILURE_TEMPORARY_NETWORK
    return FAILURE_TEMPORARY_NETWORK


def record_target_failure(target_id: str) -> int:
    """Record a failure for target_id. Returns current failure count for this target (recent window)."""
    key = (target_id or "").strip() or "unknown"
    now = _now_ts()
    if key not in _target_failures:
        _target_failures[key] = []
    _target_failures[key].append(now)
    # Keep last 10 minutes of failures
    cutoff = now - 600
    _target_failures[key] = [ts for ts in _target_failures[key] if ts >= cutoff][-_MAX_FAILURES_TRACKED:]
    return len(_target_failures[key])


def get_target_failure_count(target_id: str) -> int:
    """Return recent failure count for target_id."""
    key = (target_id or "").strip() or "unknown"
    return len(_target_failures.get(key, []))


def get_recovery_decision(
    failed_target_id: str,
    detected_failure_category: Optional[str] = None,
    raw_failure_type: Optional[str] = None,
    error_message: Optional[str] = None,
    job_id: Optional[int] = None,
    attempt: int = 0,
) -> Dict[str, Any]:
    """
    Decide recovery action for a failed job/target. Returns structured output:
    failed_job_id/target_id, detected_failure_category, recovery_action_chosen, retry_schedule, cooldown_info, timestamp.
    """
    target_id = (failed_target_id or "").strip() or "unknown"
    category = detected_failure_category or classify_failure(raw_failure_type, error_message)
    failure_count = get_target_failure_count(target_id)

    # Repeated target failure?
    if failure_count >= _REPEATED_THRESHOLD:
        category = FAILURE_REPEATED_TARGET

    retry_after_seconds: Optional[float] = None
    cooldown_until: Optional[str] = None
    action = ACTION_DELAYED_RETRY

    try:
        from amazon_research.monitoring.scraper_reliability import get_retry_delay, should_rotate_proxy
        retry_after_seconds = get_retry_delay(attempt)
    except Exception:
        retry_after_seconds = 5.0

    if category == FAILURE_REPEATED_TARGET:
        action = ACTION_SKIP_ESCALATE
        cooldown_until = (datetime.now(timezone.utc) + timedelta(seconds=_COOLDOWN_AFTER_REPEATED)).isoformat()
        retry_after_seconds = None
    elif category == FAILURE_BLOCKED_CAPTCHA:
        try:
            from amazon_research.monitoring.scraper_reliability import should_rotate_proxy
            if should_rotate_proxy("blocked"):
                action = ACTION_PROXY_ROTATION_BEFORE_RETRY
        except Exception:
            pass
        retry_after_seconds = retry_after_seconds or 10.0
    elif category == FAILURE_PROXY:
        action = ACTION_PROXY_ROTATION_BEFORE_RETRY
        retry_after_seconds = retry_after_seconds or 5.0
    elif category == FAILURE_TEMPORARY_NETWORK:
        if attempt == 0:
            action = ACTION_IMMEDIATE_RETRY
            retry_after_seconds = 2.0
        else:
            action = ACTION_DELAYED_RETRY
    elif category == FAILURE_PARSER:
        action = ACTION_DELAYED_RETRY
        retry_after_seconds = retry_after_seconds or 15.0

    if action == ACTION_TEMPORARY_TARGET_COOLDOWN:
        cooldown_until = (datetime.now(timezone.utc) + timedelta(seconds=_COOLDOWN_SECONDS)).isoformat()
        retry_after_seconds = _COOLDOWN_SECONDS

    retry_schedule: Dict[str, Any] = {}
    if retry_after_seconds is not None:
        retry_schedule["retry_after_seconds"] = round(retry_after_seconds, 1)
        retry_schedule["retry_at"] = (datetime.now(timezone.utc) + timedelta(seconds=retry_after_seconds)).isoformat()

    cooldown_info: Dict[str, Any] = {}
    if cooldown_until:
        cooldown_info["cooldown_until"] = cooldown_until
        cooldown_info["reason"] = category

    return {
        "failed_job_id": job_id,
        "target_id": target_id,
        "detected_failure_category": category,
        "recovery_action_chosen": action,
        "retry_schedule": retry_schedule,
        "cooldown_info": cooldown_info,
        "timestamp": _now_iso(),
    }


def apply_failure_and_get_decision(
    target_id: str,
    raw_failure_type: Optional[str] = None,
    error_message: Optional[str] = None,
    job_id: Optional[int] = None,
    attempt: int = 0,
) -> Dict[str, Any]:
    """Record the failure for target_id, then return get_recovery_decision. Convenience for worker/orchestrator."""
    record_target_failure(target_id)
    return get_recovery_decision(
        failed_target_id=target_id,
        raw_failure_type=raw_failure_type,
        error_message=error_message,
        job_id=job_id,
        attempt=attempt,
    )
