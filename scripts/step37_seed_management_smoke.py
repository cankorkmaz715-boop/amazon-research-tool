#!/usr/bin/env python3
"""Step 37: Category seed management – add, list, enable/disable discovery seed URLs."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, add_seed, list_seeds, set_seed_enabled, get_enabled_seed_urls

    init_db()

    # Apply discovery_seeds schema if not present (run 003 script)
    from amazon_research.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS discovery_seeds (
                id SERIAL PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                label TEXT,
                enabled BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema ensure failed: {e}") from e

    # Seed list: add two, list all
    add_seed("https://www.amazon.com/s?k=test1", label="test seed 1", enabled=True)
    add_seed("https://www.amazon.com/s?k=test2", label="test seed 2", enabled=True)
    all_seeds = list_seeds(enabled_only=None)
    seed_list_ok = len(all_seeds) >= 2 and all(s.get("url") and "id" in s for s in all_seeds)

    # Enable/disable: disable first by id, check enabled list, then re-enable
    seed_id = all_seeds[0]["id"]
    set_ok = set_seed_enabled(seed_id, False)
    enabled_after_disable = get_enabled_seed_urls()
    disabled_ok = set_ok and len(enabled_after_disable) < len(all_seeds)
    set_seed_enabled(seed_id, True)
    enabled_after_reenable = get_enabled_seed_urls()
    enable_ok = len(enabled_after_reenable) >= len(enabled_after_disable)

    print("seed management OK")
    print("seed list: OK" if seed_list_ok else "seed list: FAIL")
    print("enable/disable: OK" if (set_ok and disabled_ok and enable_ok) else "enable/disable: FAIL")

    if not (seed_list_ok and set_ok and disabled_ok and enable_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
