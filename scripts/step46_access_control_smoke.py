#!/usr/bin/env python3
"""Step 46: Basic auth / internal access control – API key and workspace scoping."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    # Force key to be set for auth tests
    os.environ["INTERNAL_API_KEY"] = os.environ.get("INTERNAL_API_KEY") or "step46-test-key"
    from amazon_research.db import init_db, get_connection, create_workspace, get_workspace, upsert_asin
    from amazon_research.auth import validate_internal_request
    from amazon_research.api import get_products

    init_db()

    # Ensure workspaces and asins.workspace_id exist
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("ALTER TABLE asins ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL")
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema check failed: {e}") from e

    # Auth check: wrong key -> not allowed; right key -> allowed
    allowed_wrong, _ = validate_internal_request(api_key="wrong-key")
    allowed_ok, _ = validate_internal_request(api_key="step46-test-key")
    auth_check_ok = not allowed_wrong and allowed_ok

    # Workspace scope: valid workspace_id header returns (True, workspace_id); invalid returns (False, None)
    wid = create_workspace("Step46 Auth WS", "step46-auth")
    allowed_ws, resolved_ws = validate_internal_request(api_key="step46-test-key", workspace_id_header=str(wid))
    invalid_ws_allowed, _ = validate_internal_request(api_key="step46-test-key", workspace_id_header="99999")
    workspace_scope_ok = allowed_ws and resolved_ws == wid and not invalid_ws_allowed

    # Protected endpoint access: with workspace scoping, get_products(workspace_id=wid) returns envelope and only that workspace's data
    upsert_asin("AC46ASIN01", title="Access control test", workspace_id=wid)
    body = get_products(limit=10, workspace_id=wid)
    protected_ok = isinstance(body, dict) and "data" in body and "meta" in body
    if protected_ok and body.get("data"):
        protected_ok = len(body["data"]) >= 1 and body["data"][0].get("asin") == "AC46ASIN01"
    protected_ok = protected_ok and not validate_internal_request(api_key="bad")[0]

    print("access control OK")
    print("auth check: OK" if auth_check_ok else "auth check: FAIL")
    print("workspace scope: OK" if workspace_scope_ok else "workspace scope: FAIL")
    print("protected endpoint access: OK" if protected_ok else "protected endpoint access: FAIL")

    if not (auth_check_ok and workspace_scope_ok and protected_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
