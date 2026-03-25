#!/usr/bin/env python3
"""Step 22: Failure tracking – persist failure count, last_error, last_attempt_at, last_success_at, skip_until."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import (
    init_db,
    get_connection,
    upsert_asin,
    get_asin_id,
    record_attempt,
    record_success,
    record_failure,
    should_skip_asin,
)

def main():
    init_db()
    # Apply Step 22 schema if not already applied
    schema_path = os.path.join(ROOT, "sql", "002_asin_attempt_state.sql")
    if os.path.isfile(schema_path):
        with open(schema_path, "r") as f:
            sql = f.read()
        conn = get_connection()
        try:
            conn.cursor().execute(sql)
            conn.commit()
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise
        conn.cursor().close()

    # Use a dedicated test ASIN so we don't affect real data
    test_asin = "B00STEP22X"
    asin_id = upsert_asin(test_asin)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM asin_attempt_state WHERE asin_id = %s", (asin_id,))
    conn.commit()
    cur.close()

    record_attempt(asin_id)
    record_failure(asin_id, "test error one")
    record_failure(asin_id, "test error two")
    record_success(asin_id)

    cur = conn.cursor()
    cur.execute(
        "SELECT failure_count, last_error, last_attempt_at, last_success_at, skip_until FROM asin_attempt_state WHERE asin_id = %s",
        (asin_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        print("State row missing")
        sys.exit(1)
    failure_count, last_error, last_attempt_at, last_success_at, skip_until = row
    assert failure_count == 0, "success should reset failure_count"
    assert last_success_at is not None, "last_success_at should be set"
    assert skip_until is None, "success should clear skip_until"

    # Trigger skip: record failure until we hit threshold (config skip_after_n_failures, default 3)
    from amazon_research.config import get_config
    thresh = get_config().skip_after_n_failures
    for _ in range(thresh):
        record_failure(asin_id, "smoke test skip trigger")
    assert should_skip_asin(asin_id), "ASIN should be skippable after N failures"

    print("failure tracking OK")
    print("retry state persisted")
    print("skip logic active")

if __name__ == "__main__":
    main()
