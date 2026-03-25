"""
Step 198: Workspace alert preferences persistence – per-workspace alert behavior, thresholds, delivery, quiet hours.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.workspace_alert_preferences")


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_json(val: Any, default: Dict[str, Any]) -> Dict[str, Any]:
    if val is None:
        return dict(default)
    if isinstance(val, dict):
        return dict(val)
    if isinstance(val, str) and val.strip():
        try:
            out = json.loads(val)
            return dict(out) if isinstance(out, dict) else dict(default)
        except Exception:
            return dict(default)
    return dict(default)


def get_workspace_alert_preferences(workspace_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """
    Return stored alert preferences row for the workspace, or None if not found or on error.
    Keys: id, workspace_id, alerts_enabled, opportunity_alerts_enabled, trend_alerts_enabled,
    portfolio_alerts_enabled, score_threshold, priority_threshold, delivery_channels_json,
    quiet_hours_json, created_at, updated_at.
    """
    if workspace_id is None:
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, alerts_enabled, opportunity_alerts_enabled, trend_alerts_enabled,
                      portfolio_alerts_enabled, score_threshold, priority_threshold,
                      delivery_channels_json, quiet_hours_json, created_at, updated_at
               FROM workspace_alert_preferences WHERE workspace_id = %s""",
            (workspace_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        score = row[6]
        if isinstance(score, Decimal):
            score = float(score)
        elif score is not None:
            try:
                score = float(score)
            except (TypeError, ValueError):
                score = 70.0
        return {
            "id": row[0],
            "workspace_id": row[1],
            "alerts_enabled": bool(row[2]) if row[2] is not None else True,
            "opportunity_alerts_enabled": bool(row[3]) if row[3] is not None else True,
            "trend_alerts_enabled": bool(row[4]) if row[4] is not None else True,
            "portfolio_alerts_enabled": bool(row[5]) if row[5] is not None else True,
            "score_threshold": score if score is not None else 70.0,
            "priority_threshold": int(row[7]) if row[7] is not None else 0,
            "delivery_channels_json": _safe_json(row[8], {}),
            "quiet_hours_json": _safe_json(row[9], {}),
            "created_at": row[10],
            "updated_at": row[11],
        }
    except Exception as e:
        logger.warning("workspace_alert_preferences read failed workspace_id=%s: %s", workspace_id, e)
        return None


def upsert_workspace_alert_preferences(
    workspace_id: int,
    preferences: Dict[str, Any],
) -> Optional[int]:
    """
    Insert or update workspace alert preferences. preferences can contain: alerts_enabled,
    opportunity_alerts_enabled, trend_alerts_enabled, portfolio_alerts_enabled, score_threshold,
    priority_threshold, delivery_channels_json, quiet_hours_json.
    Returns workspace_id on success, None on error. Logs start, success, failure.
    """
    if workspace_id is None:
        return None
    logger.info("workspace_alert_preferences upsert start workspace_id=%s", workspace_id)
    try:
        conn = _get_connection()
        cur = conn.cursor()
        alerts_enabled = preferences.get("alerts_enabled")
        alerts_enabled = bool(alerts_enabled) if alerts_enabled is not None else True
        opportunity_alerts_enabled = preferences.get("opportunity_alerts_enabled")
        opportunity_alerts_enabled = bool(opportunity_alerts_enabled) if opportunity_alerts_enabled is not None else True
        trend_alerts_enabled = preferences.get("trend_alerts_enabled")
        trend_alerts_enabled = bool(trend_alerts_enabled) if trend_alerts_enabled is not None else True
        portfolio_alerts_enabled = preferences.get("portfolio_alerts_enabled")
        portfolio_alerts_enabled = bool(portfolio_alerts_enabled) if portfolio_alerts_enabled is not None else True
        score_threshold = preferences.get("score_threshold")
        if score_threshold is not None:
            try:
                score_threshold = max(0.0, min(100.0, float(score_threshold)))
            except (TypeError, ValueError):
                score_threshold = 70.0
        else:
            score_threshold = 70.0
        priority_threshold = preferences.get("priority_threshold")
        if priority_threshold is not None:
            try:
                priority_threshold = max(0, min(100, int(priority_threshold)))
            except (TypeError, ValueError):
                priority_threshold = 0
        else:
            priority_threshold = 0
        delivery = _safe_json(preferences.get("delivery_channels_json"), {})
        quiet = _safe_json(preferences.get("quiet_hours_json"), {})
        now = _now_utc()
        cur.execute(
            """INSERT INTO workspace_alert_preferences
               (workspace_id, alerts_enabled, opportunity_alerts_enabled, trend_alerts_enabled,
                portfolio_alerts_enabled, score_threshold, priority_threshold,
                delivery_channels_json, quiet_hours_json, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
               ON CONFLICT (workspace_id) DO UPDATE SET
                 alerts_enabled = EXCLUDED.alerts_enabled,
                 opportunity_alerts_enabled = EXCLUDED.opportunity_alerts_enabled,
                 trend_alerts_enabled = EXCLUDED.trend_alerts_enabled,
                 portfolio_alerts_enabled = EXCLUDED.portfolio_alerts_enabled,
                 score_threshold = EXCLUDED.score_threshold,
                 priority_threshold = EXCLUDED.priority_threshold,
                 delivery_channels_json = EXCLUDED.delivery_channels_json,
                 quiet_hours_json = EXCLUDED.quiet_hours_json,
                 updated_at = EXCLUDED.updated_at""",
            (workspace_id, alerts_enabled, opportunity_alerts_enabled, trend_alerts_enabled,
             portfolio_alerts_enabled, score_threshold, priority_threshold,
             json.dumps(delivery), json.dumps(quiet), now, now),
        )
        conn.commit()
        cur.close()
        logger.info("workspace_alert_preferences upsert success workspace_id=%s", workspace_id)
        return workspace_id
    except Exception as e:
        logger.warning("workspace_alert_preferences upsert failure workspace_id=%s: %s", workspace_id, e)
        return None
