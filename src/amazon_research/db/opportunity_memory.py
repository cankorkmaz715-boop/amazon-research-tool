"""
Step 124: Opportunity memory layer – store discovered opportunity candidates over time.
Tracks first_seen_at, last_seen_at, score evolution, status (newly_discovered, recurring, strengthening, weakening).
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db.opportunity_memory")

STATUS_NEWLY_DISCOVERED = "newly_discovered"
STATUS_RECURRING = "recurring"
STATUS_STRENGTHENING = "strengthening"
STATUS_WEAKENING = "weakening"

MAX_SCORE_HISTORY = 50


def _get_connection():
    from amazon_research.db.connection import get_connection
    return get_connection()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def record_opportunity_seen(
    opportunity_ref: str,
    context: Optional[Dict[str, Any]] = None,
    latest_opportunity_score: Optional[float] = None,
    *,
    workspace_id: Optional[int] = None,
    alert_summary: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """
    Upsert opportunity memory: insert if new (first_seen_at, last_seen_at, status=newly_discovered),
    else update last_seen_at, latest_opportunity_score, append score_history, set status (recurring/strengthening/weakening).
    Returns row id or None.
    """
    ref = (opportunity_ref or "").strip()
    if not ref:
        return None
    ctx = context if isinstance(context, dict) else {}
    score = float(latest_opportunity_score) if latest_opportunity_score is not None else None
    alert = alert_summary if isinstance(alert_summary, dict) else {}
    now = _now_utc()

    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, first_seen_at, last_seen_at, latest_opportunity_score, score_history, status
               FROM opportunity_memory WHERE opportunity_ref = %s""",
            (ref,),
        )
        row = cur.fetchone()
        if row is None:
            score_hist = [{"at": now.isoformat(), "score": score}] if score is not None else []
            cur.execute(
                """INSERT INTO opportunity_memory
                   (opportunity_ref, workspace_id, context, first_seen_at, last_seen_at, latest_opportunity_score, score_history, alert_summary, status, updated_at)
                   VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
                   RETURNING id""",
                (
                    ref,
                    workspace_id,
                    json.dumps(ctx),
                    now,
                    now,
                    score,
                    json.dumps(score_hist),
                    json.dumps(alert),
                    STATUS_NEWLY_DISCOVERED,
                    now,
                ),
            )
            out = cur.fetchone()[0]
        else:
            rid, first_seen, last_seen, prev_score, score_hist, prev_status = row
            score_hist = score_hist if isinstance(score_hist, list) else (json.loads(score_hist) if isinstance(score_hist, str) and score_hist else [])
            if score is not None:
                score_hist.append({"at": now.isoformat(), "score": score})
                score_hist = score_hist[-MAX_SCORE_HISTORY:]
            prev_num = score_hist[-2]["score"] if len(score_hist) >= 2 else (prev_score if prev_score is not None else None)
            if prev_num is not None and score is not None:
                if score > prev_num:
                    status = STATUS_STRENGTHENING
                elif score < prev_num:
                    status = STATUS_WEAKENING
                else:
                    status = STATUS_RECURRING
            else:
                status = STATUS_RECURRING
            cur.execute(
                """UPDATE opportunity_memory
                   SET last_seen_at = %s, latest_opportunity_score = %s, score_history = %s::jsonb, alert_summary = %s::jsonb, status = %s, updated_at = %s
                   WHERE opportunity_ref = %s""",
                (now, score, json.dumps(score_hist), json.dumps(alert), status, now, ref),
            )
            out = rid
        cur.close()
        conn.commit()
        return out
    except Exception as e:
        logger.debug("record_opportunity_seen failed: %s", e)
        return None


def get_opportunity_memory_by_id(opportunity_id: int, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Return one opportunity memory row by id, optionally scoped to workspace. None if not found or wrong workspace."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if workspace_id is not None:
            cur.execute(
                """SELECT id, opportunity_ref, workspace_id, context, first_seen_at, last_seen_at,
                          latest_opportunity_score, score_history, alert_summary, status, created_at, updated_at
                   FROM opportunity_memory WHERE id = %s AND (workspace_id = %s OR workspace_id IS NULL)""",
                (opportunity_id, workspace_id),
            )
        else:
            cur.execute(
                """SELECT id, opportunity_ref, workspace_id, context, first_seen_at, last_seen_at,
                          latest_opportunity_score, score_history, alert_summary, status, created_at, updated_at
                   FROM opportunity_memory WHERE id = %s""",
                (opportunity_id,),
            )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        sh = row[7]
        if isinstance(sh, str) and sh:
            try:
                sh = json.loads(sh)
            except Exception:
                sh = []
        al = row[8]
        if isinstance(al, str) and al:
            try:
                al = json.loads(al)
            except Exception:
                al = {}
        ctx = row[3]
        if isinstance(ctx, str) and ctx:
            try:
                ctx = json.loads(ctx)
            except Exception:
                ctx = {}
        return {
            "id": row[0],
            "opportunity_ref": row[1],
            "workspace_id": row[2],
            "context": ctx or {},
            "first_seen_at": row[4],
            "last_seen_at": row[5],
            "latest_opportunity_score": float(row[6]) if row[6] is not None else None,
            "score_history": sh or [],
            "alert_summary": al or {},
            "status": row[9],
            "created_at": row[10],
            "updated_at": row[11],
        }
    except Exception as e:
        logger.debug("get_opportunity_memory_by_id failed: %s", e)
        return None


def get_opportunity_memory(opportunity_ref: str) -> Optional[Dict[str, Any]]:
    """Return one opportunity memory row as dict, or None."""
    ref = (opportunity_ref or "").strip()
    if not ref:
        return None
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, opportunity_ref, workspace_id, context, first_seen_at, last_seen_at,
                      latest_opportunity_score, score_history, alert_summary, status, created_at, updated_at
               FROM opportunity_memory WHERE opportunity_ref = %s""",
            (ref,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        sh = row[7]
        if isinstance(sh, str) and sh:
            try:
                sh = json.loads(sh)
            except Exception:
                sh = []
        al = row[8]
        if isinstance(al, str) and al:
            try:
                al = json.loads(al)
            except Exception:
                al = {}
        ctx = row[3]
        if isinstance(ctx, str) and ctx:
            try:
                ctx = json.loads(ctx)
            except Exception:
                ctx = {}
        return {
            "id": row[0],
            "opportunity_ref": row[1],
            "workspace_id": row[2],
            "context": ctx or {},
            "first_seen_at": row[4],
            "last_seen_at": row[5],
            "latest_opportunity_score": float(row[6]) if row[6] is not None else None,
            "score_history": sh or [],
            "alert_summary": al or {},
            "status": row[9],
            "created_at": row[10],
            "updated_at": row[11],
        }
    except Exception as e:
        logger.debug("get_opportunity_memory failed: %s", e)
        return None


def list_opportunity_memory(
    limit: int = 50,
    status: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List opportunity memory rows, newest last_seen_at first."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        conditions = []
        params: List[Any] = []
        if status:
            conditions.append("status = %s")
            params.append(status)
        if workspace_id is not None:
            conditions.append("(workspace_id = %s OR workspace_id IS NULL)")
            params.append(workspace_id)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(max(1, limit))
        cur.execute(
            f"""SELECT id, opportunity_ref, workspace_id, context, first_seen_at, last_seen_at,
                       latest_opportunity_score, score_history, alert_summary, status
                FROM opportunity_memory {where}
                ORDER BY last_seen_at DESC
                LIMIT %s""",
            params,
        )
        rows = cur.fetchall()
        cur.close()
        out = []
        for row in rows:
            sh = row[7]
            if isinstance(sh, str) and sh:
                try:
                    sh = json.loads(sh)
                except Exception:
                    sh = []
            al = row[8]
            if isinstance(al, str) and al:
                try:
                    al = json.loads(al)
                except Exception:
                    al = {}
            ctx = row[3]
            if isinstance(ctx, str) and ctx:
                try:
                    ctx = json.loads(ctx)
                except Exception:
                    ctx = {}
            out.append({
                "id": row[0],
                "opportunity_ref": row[1],
                "workspace_id": row[2],
                "context": ctx or {},
                "first_seen_at": row[4],
                "last_seen_at": row[5],
                "latest_opportunity_score": float(row[6]) if row[6] is not None else None,
                "score_history": sh or [],
                "alert_summary": al or {},
                "status": row[9],
            })
        return out
    except Exception as e:
        logger.debug("list_opportunity_memory failed: %s", e)
        return []
