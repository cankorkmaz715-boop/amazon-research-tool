"""
Worker queue foundation. Step 61 – jobs for discovery, refresh, scoring.
Lightweight; status and timestamps; compatible with scheduler/pipeline.
Step 69: run_job_async for async worker loops (runs sync run_job in thread).
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.worker_queue")

JOB_TYPE_DISCOVERY = "discovery"
JOB_TYPE_REFRESH = "refresh"
JOB_TYPE_SCORING = "scoring"
JOB_TYPE_CATEGORY_SCAN = "category_scan"
JOB_TYPE_KEYWORD_SCAN = "keyword_scan"
JOB_TYPE_NICHE_DISCOVERY = "niche_discovery"
JOB_TYPE_OPPORTUNITY_ALERT = "opportunity_alert"
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


# Step 63: default retry delay (seconds) before next attempt
DEFAULT_RETRY_DELAY_SEC = 60

def _row_to_job(row) -> Dict[str, Any]:
    payload = row[3]
    if isinstance(payload, str) and payload:
        try:
            payload = json.loads(payload)
        except Exception:
            payload = None
    out = {
        "id": row[0],
        "job_type": row[1],
        "workspace_id": row[2],
        "payload": payload,
        "status": row[4],
        "created_at": row[5],
        "started_at": row[6],
        "completed_at": row[7],
        "error_message": row[8],
    }
    if len(row) >= 12:
        out["retry_count"] = row[9] or 0
        out["max_retries"] = row[10] if row[10] is not None else 3
        out["next_retry_at"] = row[11]
    else:
        out["retry_count"] = 0
        out["max_retries"] = 3
        out["next_retry_at"] = None
    if len(row) >= 13:
        out["scheduled_at"] = row[12]
    else:
        out["scheduled_at"] = None
    if len(row) >= 14:
        out["claimed_by"] = row[13]
    else:
        out["claimed_by"] = None
    return out


def enqueue_job(
    job_type: str,
    workspace_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    max_retries: Optional[int] = None,
    scheduled_at: Optional[Union[datetime, str]] = None,
) -> int:
    """Enqueue a job. Returns job id. Step 63: max_retries. Step 64: scheduled_at (job not run before this time)."""
    conn = get_connection()
    cur = conn.cursor()
    jtype = (job_type or "").strip()
    payload_json = json.dumps(payload) if payload else None
    max_r = 3 if max_retries is None else max(0, max_retries)
    cur.execute(
        """
        INSERT INTO worker_jobs (job_type, workspace_id, payload, status, retry_count, max_retries, scheduled_at)
        VALUES (%s, %s, %s::jsonb, %s, 0, %s, %s)
        RETURNING id
        """,
        (jtype, workspace_id, payload_json, STATUS_PENDING, max_r, scheduled_at),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def dequeue_next(worker_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Claim next pending job (atomic, FOR UPDATE SKIP LOCKED). Step 66: set claimed_by when worker_id provided.
    Step 63/64: eligibility by next_retry_at and scheduled_at.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE worker_jobs
        SET status = %s, started_at = NOW(), claimed_by = %s
        WHERE id = (
            SELECT id FROM worker_jobs
            WHERE status = %s
            AND (next_retry_at IS NULL OR next_retry_at <= CURRENT_TIMESTAMP)
            AND (scheduled_at IS NULL OR scheduled_at <= CURRENT_TIMESTAMP)
            ORDER BY id ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id, job_type, workspace_id, payload, status, created_at, started_at, completed_at, error_message,
                  retry_count, max_retries, next_retry_at, scheduled_at, claimed_by
        """,
        (STATUS_RUNNING, (worker_id or None), STATUS_PENDING),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return _row_to_job(row) if row else None


def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Return job by id or None. Step 63/64/66: retry, scheduled_at, claimed_by."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, job_type, workspace_id, payload, status, created_at, started_at, completed_at, error_message,
               retry_count, max_retries, next_retry_at, scheduled_at, claimed_by
        FROM worker_jobs WHERE id = %s
        """,
        (job_id,),
    )
    row = cur.fetchone()
    cur.close()
    return _row_to_job(row) if row else None


def mark_job_completed(job_id: int) -> None:
    """Set job status to completed and completed_at."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE worker_jobs SET status = %s, completed_at = NOW() WHERE id = %s",
        (STATUS_COMPLETED, job_id),
    )
    cur.close()
    conn.commit()


def mark_job_failed(job_id: int, error_message: Optional[str] = None) -> None:
    """Set job status to failed and optional error_message."""
    conn = get_connection()
    cur = conn.cursor()
    msg = (error_message or "")[:2000]
    cur.execute(
        "UPDATE worker_jobs SET status = %s, completed_at = NOW(), error_message = %s WHERE id = %s",
        (STATUS_FAILED, msg or None, job_id),
    )
    cur.close()
    conn.commit()


def schedule_retry_or_mark_failed(job_id: int, error_message: Optional[str] = None) -> None:
    """
    Step 63: On job failure, either schedule a retry (if retry_count < max_retries) or mark finally failed.
    Conservative: one retry delay (DEFAULT_RETRY_DELAY_SEC), then job becomes eligible for dequeue again.
    """
    job = get_job(job_id)
    if not job:
        mark_job_failed(job_id, error_message)
        return
    retry_count = job.get("retry_count", 0) or 0
    max_retries = job.get("max_retries", 3) or 3
    msg = (error_message or "")[:2000]
    conn = get_connection()
    cur = conn.cursor()
    if retry_count < max_retries:
        cur.execute(
            """
            UPDATE worker_jobs
            SET status = %s, retry_count = retry_count + 1, next_retry_at = NOW() + INTERVAL '1 second' * %s,
                started_at = NULL, completed_at = NULL, error_message = %s, claimed_by = NULL
            WHERE id = %s
            """,
            (STATUS_PENDING, DEFAULT_RETRY_DELAY_SEC, msg or None, job_id),
        )
        logger.info(
            "job scheduled for retry",
            extra={"job_id": job_id, "retry_count": retry_count + 1, "max_retries": max_retries},
        )
    else:
        cur.execute(
            "UPDATE worker_jobs SET status = %s, completed_at = NOW(), error_message = %s WHERE id = %s",
            (STATUS_FAILED, msg or None, job_id),
        )
        logger.info("job failed after retries", extra={"job_id": job_id, "retry_count": retry_count})
    cur.close()
    conn.commit()


def get_queue_metrics() -> Dict[str, Any]:
    """
    Step 65: Lightweight queue observability. Returns counts by status and delayed (pending but not yet eligible).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT status, COUNT(*) FROM worker_jobs GROUP BY status
        """
    )
    rows = cur.fetchall()
    counts = {STATUS_PENDING: 0, STATUS_RUNNING: 0, STATUS_COMPLETED: 0, STATUS_FAILED: 0}
    for status_val, cnt in rows:
        if status_val in counts:
            counts[status_val] = cnt
    cur.execute(
        """
        SELECT COUNT(*) FROM worker_jobs
        WHERE status = %s
        AND (
            (scheduled_at IS NOT NULL AND scheduled_at > CURRENT_TIMESTAMP)
            OR (next_retry_at IS NOT NULL AND next_retry_at > CURRENT_TIMESTAMP)
        )
        """,
        (STATUS_PENDING,),
    )
    delayed = cur.fetchone()[0] or 0
    cur.close()
    return {
        "queued_count": counts[STATUS_PENDING],
        "running_count": counts[STATUS_RUNNING],
        "completed_count": counts[STATUS_COMPLETED],
        "failed_count": counts[STATUS_FAILED],
        "delayed_count": delayed,
    }


def list_jobs(
    workspace_id: Optional[int] = None,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List jobs with optional filters."""
    conn = get_connection()
    cur = conn.cursor()
    conditions = []
    params: List[Any] = []
    if workspace_id is not None:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    if status:
        conditions.append("status = %s")
        params.append(status)
    if job_type:
        conditions.append("job_type = %s")
        params.append(job_type)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)
    cur.execute(
        f"""
        SELECT id, job_type, workspace_id, payload, status, created_at, started_at, completed_at, error_message,
               retry_count, max_retries, next_retry_at, scheduled_at, claimed_by
        FROM worker_jobs {where}
        ORDER BY id DESC
        LIMIT %s
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    return [_row_to_job(r) for r in rows]


def get_job_counts_for_workspace(
    workspace_id: int,
    since_days: Optional[int] = None,
) -> Dict[str, int]:
    """
    Step 114: Per-workspace job counts for dashboard. Returns pending, completed, failed, total.
    Optional since_days filters by created_at.
    """
    conn = get_connection()
    cur = conn.cursor()
    if since_days is not None and since_days > 0:
        cur.execute(
            """
            SELECT status, COUNT(*) FROM worker_jobs
            WHERE workspace_id = %s AND created_at >= NOW() - INTERVAL '1 day' * %s
            GROUP BY status
            """,
            (workspace_id, since_days),
        )
    else:
        cur.execute(
            "SELECT status, COUNT(*) FROM worker_jobs WHERE workspace_id = %s GROUP BY status",
            (workspace_id,),
        )
    rows = cur.fetchall()
    cur.close()
    counts = {STATUS_PENDING: 0, STATUS_COMPLETED: 0, STATUS_FAILED: 0, STATUS_RUNNING: 0}
    for status, cnt in rows:
        counts[status] = cnt
    total = sum(counts.values())
    return {
        "pending": counts[STATUS_PENDING],
        "completed": counts[STATUS_COMPLETED],
        "failed": counts[STATUS_FAILED],
        "running": counts[STATUS_RUNNING],
        "total": total,
    }


def _now_utc() -> datetime:
    """Current time in UTC for scheduled_at eligibility (consistent with DB CURRENT_TIMESTAMP)."""
    return datetime.now(timezone.utc)


def run_job(job_id: int, worker_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run one job by id: dispatch to discovery/refresh/scoring bot. Compatible with current scheduler.
    If job is pending, claims it (status -> running) then runs. Step 64: skips jobs with scheduled_at in the future.
    Step 66: if job is running and claimed_by another worker_id, refuse to run (double-processing blocked).
    Returns dict: ok (bool), job_type, error (str or None), skipped (bool, optional).
    """
    job = get_job(job_id)
    if not job:
        return {"ok": False, "job_type": None, "error": "job not found"}
    if job["status"] not in (STATUS_RUNNING, STATUS_PENDING):
        return {"ok": False, "job_type": job["job_type"], "error": f"job already {job['status']}"}
    # Step 66: do not run job claimed by another worker
    claimed_by = job.get("claimed_by")
    if (
        job["status"] == STATUS_RUNNING
        and claimed_by
        and worker_id is not None
        and claimed_by != worker_id
    ):
        return {
            "ok": False,
            "job_type": job["job_type"],
            "error": "job claimed by another worker",
        }
    # Step 64: do not execute jobs scheduled for the future; release back to pending
    scheduled_at = job.get("scheduled_at")
    if scheduled_at is not None:
        now = _now_utc()
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at > now:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE worker_jobs SET status = %s, started_at = NULL, claimed_by = NULL WHERE id = %s",
                (STATUS_PENDING, job_id),
            )
            cur.close()
            conn.commit()
            logger.info("job skipped, not yet eligible", extra={"job_id": job_id, "scheduled_at": str(scheduled_at)})
            return {"ok": False, "job_type": job["job_type"], "error": "job not yet eligible (scheduled_at in future)", "skipped": True}
    # Claim if still pending (Step 66: set claimed_by when worker_id provided)
    if job["status"] == STATUS_PENDING:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE worker_jobs SET status = %s, started_at = NOW(), claimed_by = %s WHERE id = %s AND status = %s",
            (STATUS_RUNNING, worker_id or None, job_id, STATUS_PENDING),
        )
        cur.close()
        conn.commit()
    jtype = job["job_type"]
    ws_id = job.get("workspace_id")
    payload = job.get("payload") or {}
    kwargs = {"workspace_id": ws_id} if ws_id is not None else {}
    try:
        if jtype == JOB_TYPE_DISCOVERY:
            from amazon_research.bots import AsinDiscoveryBot
            AsinDiscoveryBot().run(**kwargs)
        elif jtype == JOB_TYPE_REFRESH:
            from amazon_research.bots import DataRefreshBot
            from amazon_research.config import get_config
            asin_list = payload.get("asin_list")
            if asin_list:
                DataRefreshBot().run(asin_list=asin_list, **kwargs)
            else:
                limit = payload.get("limit") or get_config().scheduler_refresh_limit
                DataRefreshBot().run(limit=limit, **kwargs)
        elif jtype == JOB_TYPE_SCORING:
            from amazon_research.bots import ScoringEngine
            from amazon_research.config import get_config
            limit = payload.get("limit") or get_config().scheduler_scoring_limit
            ScoringEngine().run(limit=limit, **kwargs)
        elif jtype == JOB_TYPE_CATEGORY_SCAN:
            from amazon_research.browser import BrowserSession
            from amazon_research.crawler import scan_category
            from amazon_research.db import update_category_seed_scan
            from datetime import datetime, timezone
            url = (payload.get("category_url") or "").strip()
            seed_id = payload.get("seed_id")
            marketplace = (payload.get("marketplace") or "DE").strip()
            if not url:
                raise ValueError("category_scan job missing category_url")
            session = BrowserSession(headless=True)
            session.start()
            try:
                result = scan_category(session, url, marketplace=marketplace)
                asins = result.get("asins") or []
                if seed_id is not None:
                    update_category_seed_scan(seed_id, datetime.now(timezone.utc), {"pool_size": len(asins), "pages_scanned": result.get("pages_scanned")})
                try:
                    from amazon_research.db import save_discovery_result
                    save_discovery_result("category", url, asins, marketplace=marketplace, scan_metadata=result)
                except Exception:
                    pass
            finally:
                session.close()
        elif jtype == JOB_TYPE_KEYWORD_SCAN:
            from amazon_research.browser import BrowserSession
            from amazon_research.crawler import scan_keyword
            from amazon_research.db import update_keyword_seed_scan
            from datetime import datetime, timezone
            keyword = (payload.get("keyword") or "").strip()
            seed_id = payload.get("seed_id")
            marketplace = (payload.get("marketplace") or "DE").strip()
            if not keyword:
                raise ValueError("keyword_scan job missing keyword")
            session = BrowserSession(headless=True)
            session.start()
            try:
                result = scan_keyword(session, keyword, marketplace=marketplace)
                asins = result.get("asins") or []
                if seed_id is not None:
                    update_keyword_seed_scan(seed_id, datetime.now(timezone.utc), {"pool_size": len(asins), "pages_scanned": result.get("pages_scanned")})
                try:
                    from amazon_research.db import save_discovery_result
                    save_discovery_result("keyword", keyword, asins, marketplace=marketplace, scan_metadata=result)
                except Exception:
                    pass
            finally:
                session.close()
        elif jtype == JOB_TYPE_NICHE_DISCOVERY:
            from amazon_research.discovery import run_niche_discovery
            run_niche_discovery(use_db=True, limit=20)
        elif jtype == JOB_TYPE_OPPORTUNITY_ALERT:
            from amazon_research.db import get_cluster_cache
            from amazon_research.alerts import evaluate_opportunity_alerts
            scope = (payload.get("scope_key") or "default").strip()
            entry = get_cluster_cache(scope_key=scope)
            clusters = (entry.get("clusters") or []) if entry else []
            current_entries = []
            if clusters:
                try:
                    from amazon_research.explorer import explore_niches
                    exp = explore_niches(clusters, use_db=True)
                    current_entries = exp.get("niches") or []
                except Exception:
                    current_entries = [{"cluster_id": c.get("cluster_id"), "opportunity_index": 0, "label": c.get("label")} for c in clusters]
            evaluate_opportunity_alerts(current_entries, previous_entries=None)
        elif jtype == "_test_force_fail":
            raise RuntimeError("test_force_fail")
        else:
            mark_job_failed(job_id, f"unknown job_type: {jtype}")
            return {"ok": False, "job_type": jtype, "error": f"unknown job_type: {jtype}"}
        mark_job_completed(job_id)
        try:
            from amazon_research.monitoring import record_worker_job_processed, record_discovery_run
            record_worker_job_processed(success=True)
            if jtype in (JOB_TYPE_CATEGORY_SCAN, JOB_TYPE_KEYWORD_SCAN, JOB_TYPE_NICHE_DISCOVERY):
                record_discovery_run()
        except Exception:
            pass
        return {"ok": True, "job_type": jtype, "error": None}
    except Exception as e:
        try:
            from amazon_research.monitoring import record_worker_job_processed
            record_worker_job_processed(success=False)
        except Exception:
            pass
        schedule_retry_or_mark_failed(job_id, str(e))
        return {"ok": False, "job_type": jtype, "error": str(e)}


async def run_job_async(job_id: int, worker_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Step 69: Async-capable job execution. Runs sync run_job in a thread so the event loop is not blocked.
    Worker-ready for async worker loops. No sync Playwright in asyncio loop.
    """
    return await asyncio.to_thread(run_job, job_id, worker_id)
