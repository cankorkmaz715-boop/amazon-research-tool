#!/usr/bin/env python3
"""Step 61: Worker queue foundation – enqueue, dequeue, status tracking, pipeline compatibility."""
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
        dequeue_next,
        get_job,
        list_jobs,
        mark_job_completed,
        mark_job_failed,
        run_job,
    )
    from amazon_research.db.worker_queue import STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, JOB_TYPE_SCORING

    init_db()

    # Ensure table exists
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_worker_jobs_status_type ON worker_jobs(status, job_type);")
    get_connection().commit()
    cur.close()

    # Job enqueue
    jid = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 2})
    job_enqueue_ok = jid is not None and jid >= 1

    # Job dequeue
    claimed = dequeue_next()
    job_dequeue_ok = claimed is not None and claimed.get("id") == jid and claimed.get("status") == STATUS_RUNNING

    # Job status tracking
    job = get_job(jid)
    status_ok = job is not None and job.get("started_at") is not None and job.get("status") == STATUS_RUNNING
    # Run job (scoring is DB-only, no browser)
    result = run_job(jid)
    job_after = get_job(jid)
    status_ok = status_ok and job_after is not None and job_after.get("status") == STATUS_COMPLETED and job_after.get("completed_at") is not None

    # Pipeline compatibility: run_job uses same bots as scheduler; we ran scoring successfully
    pipeline_ok = result.get("ok") is True and result.get("job_type") == JOB_TYPE_SCORING and result.get("error") is None
    # List jobs
    listed = list_jobs(limit=5)
    pipeline_ok = pipeline_ok and any(j["id"] == jid for j in listed)

    print("worker queue foundation OK")
    print("job enqueue: OK" if job_enqueue_ok else "job enqueue: FAIL")
    print("job dequeue: OK" if job_dequeue_ok else "job dequeue: FAIL")
    print("job status tracking: OK" if status_ok else "job status tracking: FAIL")
    print("pipeline compatibility: OK" if pipeline_ok else "pipeline compatibility: FAIL")

    if not (job_enqueue_ok and job_dequeue_ok and status_ok and pipeline_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
