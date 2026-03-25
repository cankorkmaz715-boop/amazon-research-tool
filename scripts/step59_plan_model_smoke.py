#!/usr/bin/env python3
"""Step 59: Plan model v1 – plan create, workspace plan link, quota profile link."""
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
        list_plans,
        set_workspace_plan,
        get_workspace_plan,
    )

    init_db()

    # Ensure plans table and workspace.plan_id exist
    cur = get_connection().cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            active BOOLEAN NOT NULL DEFAULT true,
            quota_profile JSONB,
            billing_metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_plans_active ON plans(active);")
    try:
        cur.execute("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS plan_id INTEGER REFERENCES plans(id) ON DELETE SET NULL;")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_plan_id ON workspaces(plan_id);")
    except Exception:
        pass
    get_connection().commit()
    cur.close()

    # Plan create: with name, active, quota_profile, billing_metadata
    quota_profile = {"discovery_run": 10, "export_csv": 5, "api_request": 100}
    plan_id = create_plan("Starter", active=True, quota_profile=quota_profile, billing_metadata={"tier": "starter"})
    plan_create_ok = plan_id is not None and plan_id >= 1
    p = get_plan(plan_id)
    plan_create_ok = plan_create_ok and p is not None and p.get("name") == "Starter" and p.get("active") is True
    plan_create_ok = plan_create_ok and p.get("quota_profile") == quota_profile and p.get("billing_metadata", {}).get("tier") == "starter"

    # Workspace plan link: set plan on workspace, get it back
    ws_id = create_workspace("Plan Test WS", slug="step59-plan-ws")
    set_workspace_plan(ws_id, plan_id)
    linked = get_workspace_plan(ws_id)
    workspace_plan_link_ok = linked is not None and linked.get("id") == plan_id and linked.get("name") == "Starter"
    set_workspace_plan(ws_id, None)
    workspace_plan_link_ok = workspace_plan_link_ok and get_workspace_plan(ws_id) is None
    set_workspace_plan(ws_id, plan_id)

    # Quota profile link: plan has quota_profile that can drive workspace quotas
    quota_profile_link_ok = p.get("quota_profile") is not None and "export_csv" in p["quota_profile"]

    print("plan model v1 OK")
    print("plan create: OK" if plan_create_ok else "plan create: FAIL")
    print("workspace plan link: OK" if workspace_plan_link_ok else "workspace plan link: FAIL")
    print("quota profile link: OK" if quota_profile_link_ok else "quota profile link: FAIL")

    if not (plan_create_ok and workspace_plan_link_ok and quota_profile_link_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
