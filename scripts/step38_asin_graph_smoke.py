#!/usr/bin/env python3
"""Step 38: ASIN relationship graph v1 – store and query ASIN-to-ASIN edges with source type."""
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
        upsert_asin,
        get_asin_id,
        add_asin_relationship,
        list_relationships,
    )

    init_db()

    # Ensure asin_relationships table exists
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS asin_relationships (
                id SERIAL PRIMARY KEY,
                from_asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
                to_asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
                source_type TEXT NOT NULL DEFAULT 'related',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(from_asin_id, to_asin_id, source_type)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_asin_relationships_from ON asin_relationships(from_asin_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_asin_relationships_to ON asin_relationships(to_asin_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_asin_relationships_source_type ON asin_relationships(source_type)")
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema ensure failed: {e}") from e

    # Ensure we have two ASINs to link
    id_a = upsert_asin("GRAPH000001", title="Graph test A")
    id_b = upsert_asin("GRAPH000002", title="Graph test B")
    id_c = upsert_asin("GRAPH000003", title="Graph test C")

    # Relationship storage: add edges with different source_type
    r1 = add_asin_relationship(id_a, id_b, source_type="related")
    r2 = add_asin_relationship(id_a, id_c, source_type="sponsored")
    r3 = add_asin_relationship(id_b, id_c, source_type="seed")
    storage_ok = r1 is not None and r2 is not None and r3 is not None

    # Duplicate insert returns None (no new row)
    r_dup = add_asin_relationship(id_a, id_b, source_type="related")
    storage_ok = storage_ok and (r_dup is None)

    # Source labeling: list and verify source_type on edges
    out_a = list_relationships(asin_id=id_a, direction="out")
    types = {row["source_type"] for row in out_a}
    labeling_ok = "related" in types and "sponsored" in types and len(out_a) >= 2
    all_rels = list_relationships(source_type="seed")
    labeling_ok = labeling_ok and len(all_rels) >= 1 and all_rels[0]["source_type"] == "seed"

    print("asin graph v1 OK")
    print("relationship storage: OK" if storage_ok else "relationship storage: FAIL")
    print("source labeling: OK" if labeling_ok else "source labeling: FAIL")

    if not (storage_ok and labeling_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
