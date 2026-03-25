"""
Step 196: Workspace configuration layer – per-workspace operational settings with safe defaults.
"""
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("workspace_configuration")

# Defaults aligned with Step 193/194/195 behavior
DEFAULT_CONFIG: Dict[str, Any] = {
    "intelligence_refresh_enabled": True,
    "intelligence_refresh_interval_minutes": 60,
    "intelligence_cache_enabled": True,
    "intelligence_cache_ttl_seconds": 300,
    "alerts_enabled": True,
}


def get_workspace_configuration(workspace_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """Return stored configuration for the workspace, or None if not found or on error."""
    if workspace_id is None:
        return None
    try:
        from amazon_research.db.workspace_configuration import get_workspace_configuration as db_get
        return db_get(workspace_id)
    except Exception as e:
        logger.warning("workspace_configuration get failed workspace_id=%s: %s", workspace_id, e)
        return None


def get_workspace_configuration_with_defaults(workspace_id: Optional[int]) -> Dict[str, Any]:
    """
    Return workspace configuration merged with safe defaults. Never returns None; missing or invalid stored values use defaults.
    Keys: intelligence_refresh_enabled, intelligence_refresh_interval_minutes, intelligence_cache_enabled,
    intelligence_cache_ttl_seconds, alerts_enabled, workspace_id.
    """
    out = dict(DEFAULT_CONFIG)
    out["workspace_id"] = workspace_id
    if workspace_id is None:
        logger.debug("workspace_configuration default fallback workspace_id=None")
        return out
    try:
        from amazon_research.db.workspace_configuration import get_workspace_configuration as db_get
        row = db_get(workspace_id)
        if not row:
            logger.debug("workspace_configuration default fallback workspace_id=%s no row", workspace_id)
            return out
        if row.get("intelligence_refresh_enabled") is not None:
            out["intelligence_refresh_enabled"] = bool(row["intelligence_refresh_enabled"])
        if row.get("intelligence_refresh_interval_minutes") is not None:
            try:
                out["intelligence_refresh_interval_minutes"] = max(1, min(10080, int(row["intelligence_refresh_interval_minutes"])))
            except (TypeError, ValueError):
                pass
        if row.get("intelligence_cache_enabled") is not None:
            out["intelligence_cache_enabled"] = bool(row["intelligence_cache_enabled"])
        if row.get("intelligence_cache_ttl_seconds") is not None:
            try:
                out["intelligence_cache_ttl_seconds"] = max(1, min(86400 * 7, int(row["intelligence_cache_ttl_seconds"])))
            except (TypeError, ValueError):
                pass
        if row.get("alerts_enabled") is not None:
            out["alerts_enabled"] = bool(row["alerts_enabled"])
        return out
    except Exception as e:
        logger.warning("workspace_configuration get_with_defaults failed workspace_id=%s: %s", workspace_id, e)
        return out


def upsert_workspace_configuration(workspace_id: Optional[int], config: Dict[str, Any]) -> Optional[int]:
    """Upsert workspace configuration. Returns workspace_id on success, None on error. Validates and clamps values."""
    if workspace_id is None:
        return None
    try:
        from amazon_research.db.workspace_configuration import upsert_workspace_configuration as db_upsert
        return db_upsert(workspace_id, config or {})
    except Exception as e:
        logger.warning("workspace_configuration upsert failed workspace_id=%s: %s", workspace_id, e)
        return None
