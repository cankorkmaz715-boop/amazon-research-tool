"""
Step 192: Workspace intelligence snapshots persistence – save and retrieve workspace intelligence summaries.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.workspace_intelligence_snapshots")

SNAPSHOT_TYPE_SUMMARY = "summary"
DEFAULT_VERSION = 1


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def save_workspace_intelligence_snapshot(
    workspace_id: int,
    summary: Dict[str, Any],
    *,
    snapshot_type: str = SNAPSHOT_TYPE_SUMMARY,
    version: int = DEFAULT_VERSION,
) -> Optional[int]:
    """
    Persist a workspace intelligence summary. Returns snapshot id or None.
    Logs save start, success, and failure with workspace_id.
    """
    if workspace_id is None:
        return None
    logger.info(
        "workspace_intelligence_snapshot save start workspace_id=%s snapshot_type=%s",
        workspace_id,
        snapshot_type,
    )
    try:
        payload = summary if isinstance(summary, dict) else {}
        summary_json = json.dumps(payload) if payload else "{}"
        generated_at = _now_utc()
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO workspace_intelligence_snapshots
               (workspace_id, snapshot_type, generated_at, summary_json, version, created_at, updated_at)
               VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s) RETURNING id""",
            (
                workspace_id,
                (snapshot_type or SNAPSHOT_TYPE_SUMMARY).strip() or SNAPSHOT_TYPE_SUMMARY,
                generated_at,
                summary_json,
                max(1, int(version) if version is not None else DEFAULT_VERSION),
                generated_at,
                generated_at,
            ),
        )
        row = cur.fetchone()
        sid = row[0] if row else None
        cur.close()
        conn.commit()
        logger.info(
            "workspace_intelligence_snapshot save success workspace_id=%s snapshot_id=%s",
            workspace_id,
            sid,
        )
        return sid
    except Exception as e:
        logger.warning(
            "workspace_intelligence_snapshot save failure workspace_id=%s: %s",
            workspace_id,
            e,
        )
        return None


def get_latest_workspace_intelligence_snapshot(
    workspace_id: Optional[int],
    *,
    snapshot_type: str = SNAPSHOT_TYPE_SUMMARY,
) -> Optional[Dict[str, Any]]:
    """
    Return the most recent snapshot for the workspace, or None if none or on error.
    Result: id, workspace_id, snapshot_type, generated_at, summary_json (parsed), version, created_at, updated_at.
    Logs read hit/miss with workspace_id.
    """
    if workspace_id is None:
        logger.debug("workspace_intelligence_snapshot read miss workspace_id=None")
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, snapshot_type, generated_at, summary_json, version, created_at, updated_at
               FROM workspace_intelligence_snapshots
               WHERE workspace_id = %s AND snapshot_type = %s
               ORDER BY generated_at DESC
               LIMIT 1""",
            (workspace_id, (snapshot_type or SNAPSHOT_TYPE_SUMMARY).strip() or SNAPSHOT_TYPE_SUMMARY),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            logger.info("workspace_intelligence_snapshot read miss workspace_id=%s", workspace_id)
            return None
        summary_raw = row[4]
        if isinstance(summary_raw, str) and summary_raw:
            try:
                summary_raw = json.loads(summary_raw)
            except Exception:
                summary_raw = {}
        if not isinstance(summary_raw, dict):
            summary_raw = {}
        logger.info(
            "workspace_intelligence_snapshot read hit workspace_id=%s snapshot_id=%s",
            workspace_id,
            row[0],
        )
        return {
            "id": row[0],
            "workspace_id": row[1],
            "snapshot_type": row[2],
            "generated_at": row[3],
            "summary_json": summary_raw,
            "version": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }
    except Exception as e:
        logger.warning(
            "workspace_intelligence_snapshot read failure workspace_id=%s: %s",
            workspace_id,
            e,
        )
        return None


def list_workspace_intelligence_snapshots(
    workspace_id: Optional[int],
    limit: int = 50,
    *,
    snapshot_type: str = SNAPSHOT_TYPE_SUMMARY,
) -> List[Dict[str, Any]]:
    """Return snapshot history for the workspace, newest first. Empty list on error."""
    if workspace_id is None:
        return []
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, workspace_id, snapshot_type, generated_at, summary_json, version, created_at, updated_at
               FROM workspace_intelligence_snapshots
               WHERE workspace_id = %s AND snapshot_type = %s
               ORDER BY generated_at DESC
               LIMIT %s""",
            (workspace_id, (snapshot_type or SNAPSHOT_TYPE_SUMMARY).strip() or SNAPSHOT_TYPE_SUMMARY, max(1, limit)),
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            summary_raw = row[4]
            if isinstance(summary_raw, str) and summary_raw:
                try:
                    summary_raw = json.loads(summary_raw)
                except Exception:
                    summary_raw = {}
            if not isinstance(summary_raw, dict):
                summary_raw = {}
            out.append({
                "id": row[0],
                "workspace_id": row[1],
                "snapshot_type": row[2],
                "generated_at": row[3],
                "summary_json": summary_raw,
                "version": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            })
        return out
    except Exception as e:
        logger.warning(
            "list_workspace_intelligence_snapshots failed workspace_id=%s: %s",
            workspace_id,
            e,
        )
        return []
