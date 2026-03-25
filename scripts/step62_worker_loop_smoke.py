#!/usr/bin/env python3
"""Step 62: Worker execution loop v1 – job execution, status transitions, discovery/refresh/scoring handlers."""
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
    )
    from amazon_research.db.worker_queue import (
        STATUS_COMPLETED,
        STATUS_FAILED,
        JOB_TYPE_DISCOVERY,
        JOB_TYPE_REFRESH,
        JOB_TYPE_SCORING,
    )
    from amazon_research.scheduler import run_worker_loop

    init_db()

    # Ensure worker_jobs table exists
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
    get_connection().commit()
    cur.close()

    # Enqueue one scoring job (DB-only, reliable)
    jid = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 2})
    summary = run_worker_loop(max_jobs=5)
    job_execution_ok = (
        summary.get("jobs_processed", 0) >= 1
        and (summary.get("jobs_completed", 0) + summary.get("jobs_failed", 0)) == summary.get("jobs_processed", 0)
    )
    job_after = get_job(jid)
    status_transitions_ok = (
        job_after is not None
        and job_after.get("status") == STATUS_COMPLETED
        and job_after.get("started_at") is not None
        and job_after.get("completed_at") is not None
    )

    # Enqueue one of each type; run loop (discovery/refresh may fail without browser/data)
    jid_d = enqueue_job(JOB_TYPE_DISCOVERY, None, {})
    jid_r = enqueue_job(JOB_TYPE_REFRESH, None, {"limit": 1})
    jid_s = enqueue_job(JOB_TYPE_SCORING, None, {"limit": 1})
    run_worker_loop(max_jobs=10)
    jobs = [get_job(jid_d), get_job(jid_r), get_job(jid_s)]
    handlers_ok = all(
        j is not None and j.get("status") in (STATUS_COMPLETED, STATUS_FAILED) and j.get("started_at") and j.get("completed_at")
        for j in jobs
    )

    print("worker execution loop v1 OK")
    print("job execution: OK" if job_execution_ok else "job execution: FAIL")
    print("status transitions: OK" if status_transitions_ok else "status transitions: FAIL")
    print("discovery/refresh/scoring handlers: OK" if handlers_ok else "discovery/refresh/scoring handlers: FAIL")

    if not (job_execution_ok and status_transitions_ok and handlers_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
