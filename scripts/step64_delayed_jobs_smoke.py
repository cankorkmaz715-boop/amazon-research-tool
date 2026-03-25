#!/usr/bin/env python3
"""Step 64: Delayed job scheduling v1 – scheduled_at, future job held, eligible job runs, worker integration."""
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
        get_job,
        dequeue_next,
    )
    from amazon_research.db.worker_queue import (
        STATUS_PENDING,
        STATUS_COMPLETED,
        JOB_TYPE_SCORING,
    )
    from amazon_research.scheduler import run_worker_loop

    init_db()

    # Ensure worker_jobs has retry + scheduled_at columns (016, 017)
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

    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=1)

    # --- Future job held: delayed job is not dequeued while scheduled_at is in the future ---
    jid_immediate = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1})
    jid_delayed = enqueue_job(
        JOB_TYPE_SCORING,
        workspace_id=None,
        payload={"limit": 1},
        scheduled_at=future,
    )
    first = dequeue_next()
    # Should claim the immediate job (lower id), not the delayed one
    future_held_ok = (
        first is not None
        and first.get("id") == jid_immediate
        and first.get("scheduled_at") is None
    )
    # Put the immediate job back to pending so we can run the loop (we only dequeued it)
    cur = get_connection().cursor()
    cur.execute(
        "UPDATE worker_jobs SET status = %s, started_at = NULL WHERE id = %s",
        (STATUS_PENDING, jid_immediate),
    )
    get_connection().commit()
    cur.close()

    # --- Eligible job runs: after setting scheduled_at to past, job can be run ---
    cur = get_connection().cursor()
    cur.execute(
        "UPDATE worker_jobs SET scheduled_at = %s WHERE id = %s",
        (now - timedelta(seconds=10), jid_delayed),
    )
    get_connection().commit()
    cur.close()
    run_worker_loop(max_jobs=5)
    job_immediate_after = get_job(jid_immediate)
    job_delayed_after = get_job(jid_delayed)
    eligible_runs_ok = (
        job_immediate_after is not None
        and job_immediate_after.get("status") == STATUS_COMPLETED
        and job_delayed_after is not None
        and job_delayed_after.get("status") == STATUS_COMPLETED
    )

    # --- Worker integration: one immediate + one delayed; only immediate runs first ---
    jid_a = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1})
    jid_b = enqueue_job(
        JOB_TYPE_SCORING,
        workspace_id=None,
        payload={"limit": 1},
        scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    run_worker_loop(max_jobs=10)
    job_a = get_job(jid_a)
    job_b = get_job(jid_b)
    worker_integration_ok = (
        job_a is not None
        and job_a.get("status") == STATUS_COMPLETED
        and job_b is not None
        and job_b.get("status") == STATUS_PENDING
        and job_b.get("scheduled_at") is not None
    )

    print("delayed job scheduling v1 OK")
    print("future job held: OK" if future_held_ok else "future job held: FAIL")
    print("eligible job runs: OK" if eligible_runs_ok else "eligible job runs: FAIL")
    print("worker integration: OK" if worker_integration_ok else "worker integration: FAIL")

    if not (future_held_ok and eligible_runs_ok and worker_integration_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
