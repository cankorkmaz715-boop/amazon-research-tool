#!/usr/bin/env python3
"""Step 65: Queue metrics / worker observability – queue counts, worker summary, failure/delayed visibility."""
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import (
        init_db,
        get_connection,
        enqueue_job,
        get_queue_metrics,
        get_job,
        mark_job_failed,
    )
    from amazon_research.db.worker_queue import (
        STATUS_PENDING,
        STATUS_COMPLETED,
        STATUS_FAILED,
        JOB_TYPE_SCORING,
    )
    from amazon_research.scheduler import run_worker_loop, get_last_worker_run_summary

    init_db()

    # Ensure worker_jobs and columns exist
    cur = get_connection().cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS worker_jobs (
            id SERIAL PRIMARY KEY,
            job_type TEXT NOT NULL,
            workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
            payload JSONB,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            error_message TEXT
        );
    """)
    for col_sql in (
        "ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3",
        "ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ",
        "ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ",
    ):
        cur.execute(col_sql)
    get_connection().commit()
    cur.close()

    # --- Queue counts: get_queue_metrics returns all expected keys and numeric counts ---
    m0 = get_queue_metrics()
    required_keys = ("queued_count", "running_count", "completed_count", "failed_count", "delayed_count")
    queue_counts_ok = all(k in m0 for k in required_keys) and all(
        isinstance(m0[k], (int, float)) for k in required_keys
    )

    # --- Worker summary: run loop, then get_last_worker_run_summary has processed/completed/failed ---
    jid = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1})
    run_worker_loop(max_jobs=5)
    last_summary = get_last_worker_run_summary()
    worker_summary_ok = (
        last_summary is not None
        and "jobs_processed" in last_summary
        and "jobs_completed" in last_summary
        and "jobs_failed" in last_summary
        and isinstance(last_summary.get("jobs_processed"), (int, float))
    )

    # --- Failure visibility: one failed job increases failed_count ---
    jid_f = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1})
    cur = get_connection().cursor()
    cur.execute("UPDATE worker_jobs SET status = %s WHERE id = %s", ("running", jid_f))
    get_connection().commit()
    cur.close()
    mark_job_failed(jid_f, "test failure")
    m_after_fail = get_queue_metrics()
    failure_visibility_ok = m_after_fail.get("failed_count", 0) >= 1

    # --- Delayed visibility: pending job with scheduled_at in future appears in delayed_count ---
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1}, scheduled_at=future)
    m_delayed = get_queue_metrics()
    delayed_visibility_ok = m_delayed.get("delayed_count", 0) >= 1

    print("queue metrics OK")
    print("queue counts: OK" if queue_counts_ok else "queue counts: FAIL")
    print("worker summary: OK" if worker_summary_ok else "worker summary: FAIL")
    print("failure visibility: OK" if failure_visibility_ok else "failure visibility: FAIL")
    print("delayed visibility: OK" if delayed_visibility_ok else "delayed visibility: FAIL")

    if not (queue_counts_ok and worker_summary_ok and failure_visibility_ok and delayed_visibility_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
