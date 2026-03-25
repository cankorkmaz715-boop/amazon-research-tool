#!/usr/bin/env python3
"""Step 73: Category seed manager v1 – seed create, list, enable/disable, scan metadata update."""
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.db import (
        init_db,
        get_connection,
        add_category_seed,
        list_category_seeds,
        get_category_seed,
        set_category_seed_active,
        update_category_seed_scan,
    )

    init_db()

    # Ensure category_seeds table exists
    cur = get_connection().cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS category_seeds (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
            marketplace TEXT NOT NULL DEFAULT 'DE',
            category_url TEXT NOT NULL UNIQUE,
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

    url1 = "https://www.amazon.de/b?node=123456"
    url2 = "https://www.amazon.de/b?node=789012"

    # --- Seed create ---
    id1 = add_category_seed(url1, marketplace="DE", label="Test Cat 1", active=True)
    id2 = add_category_seed(url2, marketplace="DE", label="Test Cat 2", active=True)
    seed_create_ok = isinstance(id1, int) and isinstance(id2, int) and id1 != id2

    # --- Seed list ---
    all_seeds = list_category_seeds()
    seed_list_ok = (
        isinstance(all_seeds, list)
        and len(all_seeds) >= 2
        and any(s.get("category_url") == url1 for s in all_seeds)
        and all("marketplace" in s and "active" in s and "label" in s for s in all_seeds)
    )

    # --- Enable/disable ---
    set_category_seed_active(id1, False)
    one = get_category_seed(id1)
    set_category_seed_active(id1, True)
    two = get_category_seed(id1)
    enable_disable_ok = one is not None and one.get("active") is False and two is not None and two.get("active") is True

    # --- Scan metadata update ---
    now = datetime.now(timezone.utc)
    update_category_seed_scan(id2, last_scanned_at=now, scan_metadata={"pages_scanned": 2, "pool_size": 10})
    updated = get_category_seed(id2)
    scan_meta_ok = (
        updated is not None
        and updated.get("last_scanned_at") is not None
        and isinstance(updated.get("scan_metadata"), dict)
        and updated.get("scan_metadata", {}).get("pages_scanned") == 2
        and updated.get("scan_metadata", {}).get("pool_size") == 10
    )

    print("category seed manager v1 OK")
    print("seed create: OK" if seed_create_ok else "seed create: FAIL")
    print("seed list: OK" if seed_list_ok else "seed list: FAIL")
    print("enable/disable: OK" if enable_disable_ok else "enable/disable: FAIL")
    print("scan metadata update: OK" if scan_meta_ok else "scan metadata update: FAIL")

    if not (seed_create_ok and seed_list_ok and enable_disable_ok and scan_meta_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
