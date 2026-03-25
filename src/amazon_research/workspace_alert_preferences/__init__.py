"""
Step 198: Workspace alert preferences – per-workspace alert behavior, thresholds, delivery, quiet hours.
"""
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("workspace_alert_preferences")

# Defaults aligned with current alert engine behavior (e.g. DEFAULT_SCORE_THRESHOLD 70.0)
DEFAULT_PREFERENCES: Dict[str, Any] = {
    "alerts_enabled": True,
    "opportunity_alerts_enabled": True,
    "trend_alerts_enabled": True,
    "portfolio_alerts_enabled": True,
    "score_threshold": 70.0,
    "priority_threshold": 0,
    "delivery_channels_json": {},
    "quiet_hours_json": {},
}


def get_workspace_alert_preferences(workspace_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """Return stored alert preferences for the workspace, or None if not found or on error."""
    if workspace_id is None:
        return None
    try:
        from amazon_research.db.workspace_alert_preferences import get_workspace_alert_preferences as db_get
        row = db_get(workspace_id)
        if row is not None:
            logger.info("workspace_alert_preferences read workspace_id=%s", workspace_id)
        return row
    except Exception as e:
        logger.warning("workspace_alert_preferences get failed workspace_id=%s: %s", workspace_id, e)
        return None


def get_workspace_alert_preferences_with_defaults(workspace_id: Optional[int]) -> Dict[str, Any]:
    """
    Return workspace alert preferences merged with safe defaults. Never returns None.
    Malformed optional JSON uses {}. Used by alert engine for gating and thresholds.
    """
    out = dict(DEFAULT_PREFERENCES)
    out["workspace_id"] = workspace_id
    if workspace_id is None:
        logger.debug("workspace_alert_preferences default fallback workspace_id=None")
        return out
    try:
        from amazon_research.db.workspace_alert_preferences import get_workspace_alert_preferences as db_get
        row = db_get(workspace_id)
        if not row:
            logger.debug("workspace_alert_preferences default fallback workspace_id=%s no row", workspace_id)
            return out
        for k in ("alerts_enabled", "opportunity_alerts_enabled", "trend_alerts_enabled", "portfolio_alerts_enabled"):
            if row.get(k) is not None:
                out[k] = bool(row[k])
        if row.get("score_threshold") is not None:
            try:
                out["score_threshold"] = max(0.0, min(100.0, float(row["score_threshold"])))
            except (TypeError, ValueError):
                pass
        if row.get("priority_threshold") is not None:
            try:
                out["priority_threshold"] = max(0, min(100, int(row["priority_threshold"])))
            except (TypeError, ValueError):
                pass
        if isinstance(row.get("delivery_channels_json"), dict):
            out["delivery_channels_json"] = dict(row["delivery_channels_json"])
        if isinstance(row.get("quiet_hours_json"), dict):
            out["quiet_hours_json"] = dict(row["quiet_hours_json"])
        return out
    except Exception as e:
        logger.warning("workspace_alert_preferences get_with_defaults failed workspace_id=%s: %s", workspace_id, e)
        return out


def upsert_workspace_alert_preferences(
    workspace_id: Optional[int],
    preferences: Dict[str, Any],
) -> Optional[int]:
    """Upsert workspace alert preferences. Returns workspace_id on success, None on error. Validates and clamps."""
    if workspace_id is None:
        return None
    try:
        from amazon_research.db.workspace_alert_preferences import upsert_workspace_alert_preferences as db_upsert
        return db_upsert(workspace_id, preferences or {})
    except Exception as e:
        logger.warning("workspace_alert_preferences upsert failed workspace_id=%s: %s", workspace_id, e)
        return None


def get_effective_alert_settings(workspace_id: Optional[int]) -> Dict[str, Any]:
    """
    Return effective alert settings for the alert engine: opportunity_alerts_enabled, score_threshold, etc.
    Use this before producing or surfacing opportunity alerts. Preserves current behavior when no prefs stored.
    """
    return get_workspace_alert_preferences_with_defaults(workspace_id)


def should_produce_opportunity_alerts(workspace_id: Optional[int]) -> bool:
    """
    Alert gating: True if both alerts_enabled and opportunity_alerts_enabled are True for the workspace.
    Logs gating decision when disabled.
    """
    prefs = get_workspace_alert_preferences_with_defaults(workspace_id)
    enabled = bool(prefs.get("alerts_enabled", True)) and bool(prefs.get("opportunity_alerts_enabled", True))
    if not enabled and workspace_id is not None:
        logger.info("workspace_alert_preferences gating: opportunity alerts disabled workspace_id=%s", workspace_id)
    return enabled
