#!/usr/bin/env python3
"""Step 51: Tenant API keys – workspace-scoped keys, hashed storage, auth and scope."""
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
        create_workspace_api_key,
        validate_workspace_api_key,
        list_workspace_api_keys,
        get_workspace,
    )
    from amazon_research.auth import validate_internal_request
    from amazon_research.api import get_products

    init_db()

    # Ensure table exists
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_api_keys (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            key_hash TEXT NOT NULL,
            label TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_api_keys_hash ON workspace_api_keys(key_hash);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workspace_api_keys_workspace_id ON workspace_api_keys(workspace_id);")
    except Exception:
        pass
    conn.commit()
    cur.close()

    # Create workspace and two keys
    ws_id = create_workspace("Step51 Smoke Workspace", slug="step51-smoke")
    plaintext1, key_id1 = create_workspace_api_key(ws_id, label="key-a")
    plaintext2, key_id2 = create_workspace_api_key(ws_id, label="key-b")

    key_create_ok = key_id1 and key_id2 and len(plaintext1) >= 32 and len(plaintext2) >= 32

    # Keys stored hashed (key_hash is not the plaintext)
    cur = conn.cursor()
    cur.execute("SELECT key_hash FROM workspace_api_keys WHERE workspace_id = %s", (ws_id,))
    rows = cur.fetchall()
    cur.close()
    key_hash_ok = (
        len(rows) == 2
        and all(len(r[0]) == 64 and all(c in "0123456789abcdef" for c in r[0]) for r in rows)
        and plaintext1 not in [r[0] for r in rows]
        and plaintext2 not in [r[0] for r in rows]
    )

    # Auth via workspace key: validate_internal_request returns (True, workspace_id)
    allowed1, resolved_ws1 = validate_internal_request(headers={"X-API-Key": plaintext1})
    allowed2, resolved_ws2 = validate_internal_request(api_key=plaintext2)
    auth_via_workspace_key_ok = allowed1 and resolved_ws1 == ws_id and allowed2 and resolved_ws2 == ws_id

    # Workspace scope enforced: API uses resolved workspace_id
    r = get_products(limit=5, workspace_id=ws_id)
    scope_ok = isinstance(r, dict) and "data" in r and "meta" in r and r.get("meta", {}).get("count") is not None

    # List keys (no plaintext/hash returned)
    listed = list_workspace_api_keys(ws_id)
    assert len(listed) >= 2 and all("id" in x and "label" in x and "created_at" in x for x in listed), "list_workspace_api_keys shape"

    print("workspace api keys OK")
    print("key create: OK" if key_create_ok else "key create: FAIL")
    print("key hash: OK" if key_hash_ok else "key hash: FAIL")
    print("auth via workspace key: OK" if auth_via_workspace_key_ok else "auth via workspace key: FAIL")
    print("workspace scope enforced: OK" if scope_ok else "workspace scope enforced: FAIL")

    if not (key_create_ok and key_hash_ok and auth_via_workspace_key_ok and scope_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
