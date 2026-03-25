#!/usr/bin/env python3
"""Step 63: Retry orchestration v1 – retry count, max retry limit, next_retry_at, final failed state, worker integration."""
import os
import sys

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
        schedule_retry_or_mark_failed,
    )
    from amazon_research.db.worker_queue import (
        STATUS_PENDING,
        STATUS_FAILED,
        JOB_TYPE_SCORING,
    )
    from amazon_research.scheduler import run_worker_loop

    init_db()

    # Ensure worker_jobs exists with retry columns (016)
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
    cur.execute("ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0")
    cur.execute("ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 3")
    cur.execute("ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ")
    get_connection().commit()
    cur.close()

    # --- Retry count: schedule_retry increments retry_count and sets next_retry_at ---
    jid1 = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1}, max_retries=3)
    cur = get_connection().cursor()
    cur.execute("UPDATE worker_jobs SET status = %s WHERE id = %s", ("running", jid1))
    get_connection().commit()
    cur.close()
    schedule_retry_or_mark_failed(jid1, "test error")
    job1 = get_job(jid1)
    retry_count_ok = (
        job1 is not None
        and job1.get("status") == STATUS_PENDING
        and job1.get("retry_count") == 1
        and job1.get("next_retry_at") is not None
    )

    # --- Max retry limit / final failed state: after exhaustion, status = failed ---
    jid2 = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1}, max_retries=1)
    cur = get_connection().cursor()
    cur.execute(
        "UPDATE worker_jobs SET status = %s, retry_count = 1 WHERE id = %s",
        ("running", jid2),
    )
    get_connection().commit()
    cur.close()
    schedule_retry_or_mark_failed(jid2, "exhausted")
    job2 = get_job(jid2)
    final_failed_ok = (
        job2 is not None
        and job2.get("status") == STATUS_FAILED
        and job2.get("completed_at") is not None
    )

    # --- Worker integration: _test_force_fail job fails twice, then final failed ---
    jid3 = enqueue_job("_test_force_fail", workspace_id=None, payload={}, max_retries=1)
    run_worker_loop(max_jobs=5)
    job3a = get_job(jid3)
    # First run: failed -> scheduled for retry (retry_count=1)
    if job3a and job3a.get("status") == STATUS_PENDING and job3a.get("next_retry_at"):
        cur = get_connection().cursor()
        cur.execute("UPDATE worker_jobs SET next_retry_at = NOW() WHERE id = %s", (jid3,))
        get_connection().commit()
        cur.close()
        run_worker_loop(max_jobs=5)
    job3b = get_job(jid3)
    worker_integration_ok = (
        job3b is not None
        and job3b.get("status") == STATUS_FAILED
        and job3b.get("retry_count", 0) >= 1
    )

    print("retry orchestration v1 OK")
    print("retry count: OK" if retry_count_ok else "retry count: FAIL")
    print("max retry limit: OK" if final_failed_ok else "max retry limit: FAIL")
    print("final failed state: OK" if final_failed_ok else "final failed state: FAIL")
    print("worker integration: OK" if worker_integration_ok else "worker integration: FAIL")

    if not (retry_count_ok and final_failed_ok and worker_integration_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
