"""
Step 209: Failsafe execution wrapper – circuit check, run with fallback order (cached, persisted, partial, controlled failure).
Never raises; stable response shape on controlled failure.
"""
from typing import Any, Callable, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("error_recovery.failsafe")


def stable_failure_response(
    workspace_id: Optional[Any] = None,
    path_key: Optional[str] = None,
    error: str = "recovery_fallback",
    fallback_type: str = "controlled_failure",
) -> Dict[str, Any]:
    """Stable response shape when no safe fallback is available."""
    return {
        "ok": False,
        "error": error,
        "fallback_type": fallback_type,
        "workspace_id": workspace_id,
        "path_key": path_key or "",
    }


def _try_fallback(
    get_fn: Optional[Callable[[], Any]],
    fallback_name: str,
    workspace_id: Any,
    path_key: str,
) -> Optional[Dict[str, Any]]:
    """Call get_fn; return result dict if valid; else None. Never raises. Accepts any dict (cached/persisted/partial)."""
    if get_fn is None:
        return None
    try:
        out = get_fn()
        if out is not None and isinstance(out, dict):
            logger.info(
                "error_recovery recovery fallback used workspace_id=%s path_key=%s fallback_type=%s",
                workspace_id, path_key, fallback_name,
                extra={"workspace_id": workspace_id, "path_key": path_key, "fallback_type": fallback_name},
            )
            return out
    except Exception as e:
        logger.debug("error_recovery fallback %s failed: %s", fallback_name, e)
    return None


def run_with_failsafe(
    fn: Callable[[], Dict[str, Any]],
    workspace_id: Optional[int] = None,
    path_key: str = "default",
    get_cached: Optional[Callable[[], Any]] = None,
    get_persisted: Optional[Callable[[], Any]] = None,
    get_partial: Optional[Callable[[], Any]] = None,
    treat_ok_false_as_failure: bool = True,
) -> Dict[str, Any]:
    """
    Run fn() with circuit and fallback. Never raises.
    - If circuit suppressed: return get_cached() or get_persisted() or get_partial() or stable_failure_response().
    - Run fn(). On success: record_success, return result.
    - On failure (exception or result ok=False): record_failure, then try get_cached, get_persisted, get_partial, else stable_failure_response.
    get_* callables can return a dict (prefer ok=True for cache/persisted). treat_ok_false_as_failure: if True, result with ok=False is treated as failure and triggers fallback chain.
    """
    path_key = (path_key or "default").strip()
    try:
        from amazon_research.error_recovery.circuit import is_suppressed, record_failure, record_success
    except Exception as e:
        logger.warning("error_recovery recovery metadata fallback/default behavior used: %s", e)
        try:
            return fn()
        except Exception as ex:
            return stable_failure_response(workspace_id, path_key, error=str(ex))

    suppressed, retry_after = is_suppressed(workspace_id, path_key)
    if suppressed:
        logger.info(
            "error_recovery execution wrapped with failsafe; circuit suppressed workspace_id=%s path_key=%s",
            workspace_id, path_key,
            extra={"workspace_id": workspace_id, "path_key": path_key, "retry_after_seconds": retry_after},
        )
        for name, get_fn in [("cached", get_cached), ("persisted", get_persisted), ("partial", get_partial)]:
            out = _try_fallback(get_fn, name, workspace_id, path_key)
            if out is not None:
                return out
        return stable_failure_response(
            workspace_id, path_key,
            error="circuit_suppressed",
            fallback_type="controlled_failure",
        )

    logger.debug("error_recovery execution wrapped with failsafe workspace_id=%s path_key=%s", workspace_id, path_key)
    try:
        result = fn()
        if not isinstance(result, dict):
            record_failure(workspace_id, path_key)
            for name, get_fn in [("cached", get_cached), ("persisted", get_persisted), ("partial", get_partial)]:
                out = _try_fallback(get_fn, name, workspace_id, path_key)
                if out is not None:
                    return out
            return stable_failure_response(workspace_id, path_key, error="invalid_result")
        if result.get("ok") is True:
            record_success(workspace_id, path_key)
            return result
        if treat_ok_false_as_failure:
            record_failure(workspace_id, path_key)
            for name, get_fn in [("cached", get_cached), ("persisted", get_persisted), ("partial", get_partial)]:
                out = _try_fallback(get_fn, name, workspace_id, path_key)
                if out is not None:
                    return out
        return result
    except Exception as e:
        logger.warning("error_recovery failsafe caught exception workspace_id=%s path_key=%s: %s", workspace_id, path_key, e)
        record_failure(workspace_id, path_key)
        for name, get_fn in [("cached", get_cached), ("persisted", get_persisted), ("partial", get_partial)]:
            out = _try_fallback(get_fn, name, workspace_id, path_key)
            if out is not None:
                return out
        return stable_failure_response(workspace_id, path_key, error=str(e))
