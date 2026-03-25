"""
Step 196: Workspace configuration persistence – get and upsert per-workspace operational settings.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.workspace_configuration")


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_workspace_configuration(workspace_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """
    Return the stored configuration row for the workspace, or None if not found or on error.
    Keys: id, workspace_id, intelligence_refresh_enabled, intelligence_refresh_interval_minutes,
    intelligence_cache_enabled, intelligence_cache_ttl_seconds, alerts_enabled, created_at, updated_at.
    """
    if workspace_id is None:
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, intelligence_refresh_enabled, intelligence_refresh_interval_minutes,
                      intelligence_cache_enabled, intelligence_cache_ttl_seconds, alerts_enabled, created_at, updated_at
               FROM workspace_configuration WHERE workspace_id = %s""",
            (workspace_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return {
            "id": row[0],
            "workspace_id": row[1],
            "intelligence_refresh_enabled": bool(row[2]) if row[2] is not None else True,
            "intelligence_refresh_interval_minutes": int(row[3]) if row[3] is not None else 60,
            "intelligence_cache_enabled": bool(row[4]) if row[4] is not None else True,
            "intelligence_cache_ttl_seconds": int(row[5]) if row[5] is not None else 300,
            "alerts_enabled": bool(row[6]) if row[6] is not None else True,
            "created_at": row[7],
            "updated_at": row[8],
        }
    except Exception as e:
        logger.warning("get_workspace_configuration failed workspace_id=%s: %s", workspace_id, e)
        return None


def upsert_workspace_configuration(
    workspace_id: int,
    config: Dict[str, Any],
) -> Optional[int]:
    """
    Insert or update workspace configuration. config can contain: intelligence_refresh_enabled,
    intelligence_refresh_interval_minutes, intelligence_cache_enabled, intelligence_cache_ttl_seconds, alerts_enabled.
    Returns workspace_id on success, None on error. Logs start, success, failure.
    """
    if workspace_id is None:
        return None
    logger.info("workspace_configuration upsert start workspace_id=%s", workspace_id, extra={"workspace_id": workspace_id})
    try:
        conn = _get_connection()
        cur = conn.cursor()
        refresh_enabled = config.get("intelligence_refresh_enabled")
        if refresh_enabled is not None:
            refresh_enabled = bool(refresh_enabled)
        else:
            refresh_enabled = True
        refresh_interval = config.get("intelligence_refresh_interval_minutes")
        if refresh_interval is not None:
            try:
                refresh_interval = max(1, min(10080, int(refresh_interval)))
            except (TypeError, ValueError):
                refresh_interval = 60
        else:
            refresh_interval = 60
        cache_enabled = config.get("intelligence_cache_enabled")
        if cache_enabled is not None:
            cache_enabled = bool(cache_enabled)
        else:
            cache_enabled = True
        cache_ttl = config.get("intelligence_cache_ttl_seconds")
        if cache_ttl is not None:
            try:
                cache_ttl = max(1, min(86400 * 7, int(cache_ttl)))
            except (TypeError, ValueError):
                cache_ttl = 300
        else:
            cache_ttl = 300
        alerts_enabled = config.get("alerts_enabled")
        if alerts_enabled is not None:
            alerts_enabled = bool(alerts_enabled)
        else:
            alerts_enabled = True
        now = _now_utc()
        cur.execute(
            """INSERT INTO workspace_configuration
               (workspace_id, intelligence_refresh_enabled, intelligence_refresh_interval_minutes,
                intelligence_cache_enabled, intelligence_cache_ttl_seconds, alerts_enabled, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (workspace_id) DO UPDATE SET
                 intelligence_refresh_enabled = EXCLUDED.intelligence_refresh_enabled,
                 intelligence_refresh_interval_minutes = EXCLUDED.intelligence_refresh_interval_minutes,
                 intelligence_cache_enabled = EXCLUDED.intelligence_cache_enabled,
                 intelligence_cache_ttl_seconds = EXCLUDED.intelligence_cache_ttl_seconds,
                 alerts_enabled = EXCLUDED.alerts_enabled,
                 updated_at = EXCLUDED.updated_at""",
            (workspace_id, refresh_enabled, refresh_interval, cache_enabled, cache_ttl, alerts_enabled, now, now),
        )
        conn.commit()
        cur.close()
        logger.info("workspace_configuration upsert success workspace_id=%s", workspace_id, extra={"workspace_id": workspace_id})
        return workspace_id
    except Exception as e:
        logger.warning("workspace_configuration upsert failure workspace_id=%s: %s", workspace_id, e, extra={"workspace_id": workspace_id})
        return None
