#!/usr/bin/env python3
"""Step 66: Multi-worker readiness v1 – safe claim, double-processing blocked, worker identity, state transition safety."""
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
        dequeue_next,
        run_job,
    )
    from amazon_research.db.worker_queue import (
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_COMPLETED,
        JOB_TYPE_SCORING,
    )

    init_db()

    # Ensure worker_jobs has claimed_by and other columns
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

    # --- Safe claim: two dequeues return two different jobs (no double-claim) ---
    j1 = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1})
    j2 = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1})
    claim1 = dequeue_next(worker_id="worker-1")
    claim2 = dequeue_next(worker_id="worker-2")
    safe_claim_ok = (
        claim1 is not None
        and claim2 is not None
        and claim1["id"] != claim2["id"]
    )
    # Complete the two claimed jobs so queue is clean for later tests
    if claim1:
        run_job(claim1["id"], worker_id="worker-1")
    if claim2:
        run_job(claim2["id"], worker_id="worker-2")

    # --- Double-processing blocked: job claimed by A is not runnable by B ---
    j3 = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1})
    claim_a = dequeue_next(worker_id="A")
    assert claim_a is not None and claim_a["id"] == j3
    result_b = run_job(j3, worker_id="B")
    double_block_ok = (
        result_b.get("ok") is False
        and "claimed by another worker" in (result_b.get("error") or "")
    )
    result_a = run_job(j3, worker_id="A")
    state_after_a_ok = result_a.get("ok") is True and get_job(j3) and get_job(j3).get("status") == STATUS_COMPLETED

    # --- Worker identity: claimed_by set on claim ---
    j4 = enqueue_job(JOB_TYPE_SCORING, workspace_id=None, payload={"limit": 1})
    claim_w1 = dequeue_next(worker_id="w1")
    worker_identity_ok = (
        claim_w1 is not None
        and claim_w1.get("claimed_by") == "w1"
        and get_job(claim_w1["id"]) and get_job(claim_w1["id"]).get("claimed_by") == "w1"
    )
    run_job(claim_w1["id"], worker_id="w1")  # complete it so queue is clean

    # --- State transition safety: pending -> running (only one claim); running -> completed by claimer ---
    state_transition_ok = safe_claim_ok and double_block_ok and state_after_a_ok

    print("multi-worker readiness v1 OK")
    print("safe claim: OK" if safe_claim_ok else "safe claim: FAIL")
    print("double-processing blocked: OK" if double_block_ok else "double-processing blocked: FAIL")
    print("worker identity: OK" if worker_identity_ok else "worker identity: FAIL")
    print("state transition safety: OK" if state_transition_ok else "state transition safety: FAIL")

    if not (safe_claim_ok and double_block_ok and worker_identity_ok and state_transition_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
