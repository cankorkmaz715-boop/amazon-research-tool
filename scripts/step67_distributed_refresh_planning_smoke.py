#!/usr/bin/env python3
"""Step 67: Distributed refresh planning v1 – candidate selection, priority ordering, batch partitioning, queue readiness."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_connection, enqueue_job, get_job
    from amazon_research.planner import get_refresh_candidates, build_refresh_plan
    from amazon_research.db.worker_queue import JOB_TYPE_REFRESH

    init_db()

    # Ensure worker_jobs exists for queue readiness test
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
        "ALTER TABLE worker_jobs ADD COLUMN IF NOT EXISTS claimed_by TEXT",
    ):
        cur.execute(col_sql)
    get_connection().commit()
    cur.close()

    # --- Candidate selection: returns list of {asin_id, asin} ---
    candidates = get_refresh_candidates(workspace_id=None, limit=20)
    candidate_ok = isinstance(candidates, list) and all(
        isinstance(c, dict) and "asin_id" in c and "asin" in c for c in candidates
    )

    # --- Priority ordering: same call with ordering; structure and optional order ---
    ordered = get_refresh_candidates(workspace_id=None, limit=10, ordering="oldest_first")
    priority_ok = isinstance(ordered, list) and (len(ordered) == 0 or "asin_id" in ordered[0])

    # --- Batch partitioning: batches are lists of ASIN strings, batch_count and candidates_count ---
    plan = build_refresh_plan(workspace_id=None, candidate_limit=30, batch_size=5)
    batch_ok = (
        "candidates" in plan
        and "batches" in plan
        and "candidates_count" in plan
        and "batch_count" in plan
        and "ordering" in plan
        and isinstance(plan["batches"], list)
        and all(isinstance(b, list) and all(isinstance(x, str) for x in b) for b in plan["batches"])
        and plan["candidates_count"] == len(plan["candidates"])
    )

    # --- Queue readiness: enqueue a refresh job with asin_list from plan; job exists and payload correct ---
    asin_list = plan["batches"][0] if plan["batches"] else []
    jid = enqueue_job(JOB_TYPE_REFRESH, workspace_id=None, payload={"asin_list": asin_list})
    job = get_job(jid)
    queue_ok = (
        job is not None
        and job.get("job_type") == JOB_TYPE_REFRESH
        and job.get("payload", {}).get("asin_list") == asin_list
    )

    print("distributed refresh planning v1 OK")
    print("candidate selection: OK" if candidate_ok else "candidate selection: FAIL")
    print("priority ordering: OK" if priority_ok else "priority ordering: FAIL")
    print("batch partitioning: OK" if batch_ok else "batch partitioning: FAIL")
    print("queue readiness: OK" if queue_ok else "queue readiness: FAIL")

    if not (candidate_ok and priority_ok and batch_ok and queue_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
