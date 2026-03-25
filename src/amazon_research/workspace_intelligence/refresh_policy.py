"""
Step 193: Workspace intelligence refresh policy – determine which workspaces require a refresh.
Rules: refresh if no snapshot exists; refresh if latest snapshot is older than X minutes;
skip if snapshot was recently generated. Env: REFRESH_INTERVAL_MINUTES, REFRESH_BATCH, STALE_MINUTES.
"""
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("workspace_intelligence.refresh_policy")

# Env keys
ENV_REFRESH_INTERVAL_MINUTES = "WORKSPACE_INTELLIGENCE_REFRESH_INTERVAL_MINUTES"
ENV_REFRESH_BATCH = "WORKSPACE_INTELLIGENCE_REFRESH_BATCH"
ENV_STALE_MINUTES = "WORKSPACE_INTELLIGENCE_STALE_MINUTES"

# Defaults
DEFAULT_REFRESH_INTERVAL_MINUTES = 60
DEFAULT_REFRESH_BATCH = 10
DEFAULT_STALE_MINUTES = 60


def get_refresh_interval_minutes() -> int:
    """Cycle interval in minutes (how often the refresh cycle may run). From env or default."""
    try:
        v = os.environ.get(ENV_REFRESH_INTERVAL_MINUTES, "").strip()
        if v:
            return max(1, int(v))
    except (ValueError, TypeError):
        pass
    return DEFAULT_REFRESH_INTERVAL_MINUTES


def get_refresh_batch() -> int:
    """Max workspaces to refresh per cycle. From env or default."""
    try:
        v = os.environ.get(ENV_REFRESH_BATCH, "").strip()
        if v:
            return max(1, min(500, int(v)))
    except (ValueError, TypeError):
        pass
    return DEFAULT_REFRESH_BATCH


def get_stale_minutes() -> int:
    """Consider snapshot stale (need refresh) if older than this many minutes. From env or default."""
    try:
        v = os.environ.get(ENV_STALE_MINUTES, "").strip()
        if v:
            return max(1, int(v))
    except (ValueError, TypeError):
        pass
    return DEFAULT_STALE_MINUTES


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def workspaces_requiring_refresh(
    workspace_ids: Optional[List[int]] = None,
    batch_limit: Optional[int] = None,
    stale_minutes: Optional[int] = None,
) -> List[int]:
    """
    Return workspace ids that need a refresh: no snapshot, or latest snapshot older than stale_minutes.
    If workspace_ids not provided, lists all workspaces. Returns up to batch_limit ids (default from env).
    Never raises; returns [] on error and logs.
    """
    limit = batch_limit if batch_limit is not None else get_refresh_batch()
    stale = stale_minutes if stale_minutes is not None else get_stale_minutes()
    cutoff = _now_utc() - timedelta(minutes=stale)
    out: List[int] = []

    try:
        if workspace_ids is None:
            from amazon_research.db import list_workspaces
            workspaces = list_workspaces() or []
            workspace_ids = [w.get("id") for w in workspaces if w.get("id") is not None]
    except Exception as e:
        logger.warning("workspace_intelligence refresh_policy list_workspaces failed: %s", e)
        return []

    try:
        from amazon_research.db.workspace_intelligence_snapshots import get_latest_workspace_intelligence_snapshot
    except Exception as e:
        logger.warning("workspace_intelligence refresh_policy import snapshots failed: %s", e)
        return []

    for wid in workspace_ids or []:
        if len(out) >= limit:
            break
        try:
            # Step 196: respect workspace intelligence_refresh_enabled
            try:
                from amazon_research.workspace_configuration import get_workspace_configuration_with_defaults
                cfg = get_workspace_configuration_with_defaults(wid)
                if not cfg.get("intelligence_refresh_enabled", True):
                    continue
            except Exception:
                pass
            snap = get_latest_workspace_intelligence_snapshot(wid)
            if snap is None:
                out.append(wid)
                continue
            generated_at = snap.get("generated_at")
            if generated_at is None:
                out.append(wid)
                continue
            if hasattr(generated_at, "replace") and getattr(generated_at, "tzinfo", None) is None:
                generated_at = generated_at.replace(tzinfo=timezone.utc)
            if generated_at < cutoff:
                out.append(wid)
        except Exception as e:
            logger.warning("workspace_intelligence refresh_policy check workspace_id=%s: %s", wid, e)
            out.append(wid)
    return out
