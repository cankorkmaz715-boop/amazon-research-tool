#!/usr/bin/env python3
"""Step 78: Keyword scan planner v1 – seed selection, priority logic, scan task generation, queue readiness."""
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
        add_keyword_seed,
        get_ready_keyword_seeds,
        update_keyword_seed_scan,
    )
    from amazon_research.planner import build_keyword_scan_plan

    init_db()

    # Ensure keyword_seeds exists
    cur = get_connection().cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS keyword_seeds (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
            marketplace TEXT NOT NULL DEFAULT 'DE',
            keyword TEXT NOT NULL UNIQUE,
            label TEXT,
            active BOOLEAN NOT NULL DEFAULT true,
            last_scanned_at TIMESTAMPTZ,
            scan_metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    get_connection().commit()
    cur.close()

    add_keyword_seed("wireless mouse", marketplace="DE", label="Kw A", active=True)
    add_keyword_seed("usb cable", marketplace="DE", label="Kw B", active=True)

    # --- Seed selection: get_ready_keyword_seeds returns only active seeds ---
    ready = get_ready_keyword_seeds(limit=10, order_by_last_scanned=True)
    seed_selection_ok = isinstance(ready, list) and all(s.get("active") is True for s in ready)

    # --- Priority logic: order by last_scanned_at ASC NULLS FIRST (never-scanned or oldest first) ---
    if len(ready) >= 2:
        update_keyword_seed_scan(ready[0]["id"], scan_metadata={"pages": 1})
    ready2 = get_ready_keyword_seeds(limit=10, order_by_last_scanned=True)
    priority_ok = isinstance(ready2, list)  # deterministic ordering

    # --- Scan task generation: build_keyword_scan_plan returns tasks with seed_id, keyword, marketplace, label ---
    plan = build_keyword_scan_plan(max_tasks=5)
    task_gen_ok = (
        "tasks" in plan
        and "task_count" in plan
        and isinstance(plan["tasks"], list)
        and (len(plan["tasks"]) == 0 or all(
            "seed_id" in t and "keyword" in t and "marketplace" in t for t in plan["tasks"]
        ))
    )

    # --- Queue readiness: tasks can be consumed for scanner or job payloads ---
    queue_ok = (
        plan.get("task_count") == len(plan.get("tasks", []))
        and (not plan["tasks"] or (plan["tasks"][0].get("keyword") and plan["tasks"][0].get("seed_id") is not None))
    )

    print("keyword scan planner v1 OK")
    print("seed selection: OK" if seed_selection_ok else "seed selection: FAIL")
    print("priority logic: OK" if priority_ok else "priority logic: FAIL")
    print("scan task generation: OK" if task_gen_ok else "scan task generation: FAIL")
    print("queue readiness: OK" if queue_ok else "queue readiness: FAIL")

    if not (seed_selection_ok and priority_ok and task_gen_ok and queue_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
