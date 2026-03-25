"""
Step 206: Decision path guards – rate limit + cooldown checks for read and refresh paths.
Reuses rate_limit module; never crashes.
"""
from typing import Optional, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("decision_hardening.guards")

# Path keys for refresh endpoints (must match usage in API)
PATH_INTELLIGENCE_REFRESH = "intelligence_refresh"
PATH_STRATEGY_REFRESH = "strategy_refresh"
PATH_PORTFOLIO_RECOMMENDATIONS_REFRESH = "portfolio_recommendations_refresh"
PATH_MARKET_ENTRY_REFRESH = "market_entry_signals_refresh"
PATH_RISK_DETECTION_REFRESH = "risk_detection_refresh"
PATH_STRATEGIC_SCORES_REFRESH = "strategic_scores_refresh"


def _get_decision_read_limit(workspace_id: Optional[int]) -> int:
    """Limit for decision-read bucket. Uses rate_limit.get_effective_rate_limit when bucket is decision_read."""
    try:
        from amazon_research.rate_limit import get_effective_rate_limit
        return get_effective_rate_limit(workspace_id, "decision_read")
    except Exception as e:
        logger.warning("decision_hardening fallback policy used for read limit: %s", e)
        try:
            from amazon_research.decision_hardening.policy import get_read_max_per_minute
            return get_read_max_per_minute()
        except Exception:
            return 60


def _get_decision_refresh_limit(workspace_id: Optional[int]) -> int:
    """Limit for decision-refresh bucket."""
    try:
        from amazon_research.rate_limit import get_effective_rate_limit
        return get_effective_rate_limit(workspace_id, "decision_refresh")
    except Exception as e:
        logger.warning("decision_hardening fallback policy used for refresh limit: %s", e)
        try:
            from amazon_research.decision_hardening.policy import get_refresh_max_per_minute
            return get_refresh_max_per_minute()
        except Exception:
            return 10


def check_decision_read_allowed(workspace_id: Optional[int]) -> Tuple[bool, Optional[int]]:
    """
    Check if a decision READ path is allowed (rate limit). Returns (allowed, retry_after_seconds).
    On failure or invalid workspace, returns (True, None) so we do not block.
    """
    if workspace_id is None:
        return True, None
    try:
        from amazon_research.rate_limit import check_rate_limit
        limit = _get_decision_read_limit(workspace_id)
        allowed, retry_after = check_rate_limit(workspace_id, "decision_read", limit, 60.0)
        if not allowed:
            logger.info(
                "decision_hardening rate limit block read workspace_id=%s retry_after=%s",
                workspace_id, retry_after,
                extra={"workspace_id": workspace_id, "retry_after_seconds": retry_after},
            )
        return allowed, retry_after
    except Exception as e:
        logger.warning("decision_hardening read guard failed workspace_id=%s: %s", workspace_id, e)
        return True, None


def record_decision_read(workspace_id: Optional[int]) -> None:
    """Call after a decision READ request was allowed and served."""
    if workspace_id is None:
        return
    try:
        from amazon_research.rate_limit import record_rate_limit
        record_rate_limit(workspace_id, "decision_read")
    except Exception:
        pass


def check_decision_refresh_allowed(workspace_id: Optional[int], path_key: str) -> Tuple[bool, Optional[int], bool]:
    """
    Check if a decision REFRESH is allowed: (1) cooldown for same workspace+path, (2) rate limit.
    Returns (allowed, retry_after_seconds, suppressed_by_cooldown).
    suppressed_by_cooldown True means duplicate refresh suppression (not general rate limit).
    """
    if workspace_id is None or not (path_key or "").strip():
        return True, None, False
    try:
        from amazon_research.decision_hardening.cooldown import check_refresh_cooldown
        cooldown_ok, retry = check_refresh_cooldown(workspace_id, path_key)
        if not cooldown_ok:
            return False, retry, True
    except Exception as e:
        logger.warning("decision_hardening cooldown check failed workspace_id=%s path_key=%s: %s", workspace_id, path_key, e)

    try:
        from amazon_research.rate_limit import check_rate_limit
        limit = _get_decision_refresh_limit(workspace_id)
        allowed, retry_after = check_rate_limit(workspace_id, "decision_refresh", limit, 60.0)
        if not allowed:
            logger.info(
                "decision_hardening rate limit block refresh workspace_id=%s path_key=%s retry_after=%s",
                workspace_id, path_key, retry_after,
                extra={"workspace_id": workspace_id, "path_key": path_key, "retry_after_seconds": retry_after},
            )
        return allowed, retry_after, False
    except Exception as e:
        logger.warning("decision_hardening refresh guard failed workspace_id=%s path_key=%s: %s", workspace_id, path_key, e)
        return True, None, False


def record_decision_refresh(workspace_id: Optional[int], path_key: str) -> None:
    """Call after a decision REFRESH completed successfully. Updates cooldown and rate-limit bucket."""
    if workspace_id is None or not (path_key or "").strip():
        return
    try:
        from amazon_research.decision_hardening.cooldown import record_refresh_done
        record_refresh_done(workspace_id, path_key)
    except Exception:
        pass
    try:
        from amazon_research.rate_limit import record_rate_limit
        record_rate_limit(workspace_id, "decision_refresh")
    except Exception:
        pass
