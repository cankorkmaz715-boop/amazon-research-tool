#!/usr/bin/env python3
"""Step 60: Plan enforcement – plan-aware quota, rate limit, billing context, SaaS core review."""
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
        create_workspace,
        create_plan,
        get_plan,
        set_workspace_plan,
        get_workspace_plan,
        check_quota,
        record_usage,
        record_billable_event,
    )
    from amazon_research.rate_limit import get_effective_rate_limit

    init_db()

    # Ensure plans and workspace.plan_id exist
    cur = get_connection().cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, active BOOLEAN NOT NULL DEFAULT true,
            quota_profile JSONB, billing_metadata JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    try:
        cur.execute("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS plan_id INTEGER REFERENCES plans(id) ON DELETE SET NULL;")
    except Exception:
        pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billable_events (
            id SERIAL PRIMARY KEY, workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), metadata JSONB
        );
    """)
    get_connection().commit()
    cur.close()

    ws = create_workspace("Plan Enforce WS", slug="step60-plan-enforce-ws")
    # Plan with quota_profile and billing_metadata (rate limits)
    plan_id = create_plan(
        "Starter",
        active=True,
        quota_profile={"export_csv": 10, "api_request": 50},
        billing_metadata={"rate_limit_api_per_minute": 30, "rate_limit_export_per_minute": 5},
    )
    set_workspace_plan(ws, plan_id)

    # Plan-aware quota: no workspace_quotas row; check_quota uses plan.quota_profile
    result = check_quota(ws, "export_csv")
    plan_quota_ok = result.get("limit") == 10 and "allowed" in result and "used" in result

    # Plan-aware rate limit: get_effective_rate_limit returns plan's value
    api_limit = get_effective_rate_limit(ws, "api")
    export_limit = get_effective_rate_limit(ws, "export")
    plan_rate_ok = api_limit == 30 and export_limit == 5

    # Billing context: record_billable_event injects plan_id and plan_name into metadata
    record_billable_event(ws, "api_request", {"endpoint": "products"})
    cur = get_connection().cursor()
    cur.execute("SELECT metadata FROM billable_events WHERE workspace_id = %s ORDER BY id DESC LIMIT 1", (ws,))
    row = cur.fetchone()
    cur.close()
    meta = row[0] if row else None
    if isinstance(meta, str):
        import json
        meta = json.loads(meta) if meta else None
    billing_context_ok = meta is not None and meta.get("plan_id") == plan_id and meta.get("plan_name") == "Starter"

    # SaaS core review: run review script and expect exit 0
    import subprocess
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "step60_saas_core_review.py")],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": os.path.join(ROOT, "src")},
        capture_output=True,
        text=True,
    )
    saas_review_ok = r.returncode == 0 and "SaaS core review" in (r.stdout or r.stderr or "")

    print("plan enforcement OK")
    print("plan-aware quota: OK" if plan_quota_ok else "plan-aware quota: FAIL")
    print("plan-aware rate limit: OK" if plan_rate_ok else "plan-aware rate limit: FAIL")
    print("billing context: OK" if billing_context_ok else "billing context: FAIL")
    print("saas core review: OK" if saas_review_ok else "saas core review: FAIL")

    if not (plan_quota_ok and plan_rate_ok and billing_context_ok and saas_review_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
