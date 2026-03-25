#!/usr/bin/env python3
"""Step 40: Controlled graph expansion v1 – small limited expansion from ASIN relationship graph."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_connection, upsert_asin, get_asin_id, add_asin_relationship
    from amazon_research.bots.graph_expansion import run_graph_expansion

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
        cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise SystemExit(f"Schema ensure failed: {e}") from e

    # Seed graph: a -> b, a -> c, b -> c so we have 2 nodes with out-edges and 3 unique ASINs
    id_a = upsert_asin("EXPAND001", title="Expand A")
    id_b = upsert_asin("EXPAND002", title="Expand B")
    id_c = upsert_asin("EXPAND003", title="Expand C")
    add_asin_relationship(id_a, id_b, "related")
    add_asin_relationship(id_a, id_c, "sponsored")
    add_asin_relationship(id_b, id_c, "related")

    result = run_graph_expansion()

    ok = (
        isinstance(result, dict)
        and "nodes_visited" in result
        and "new_asins" in result
        and "deduped" in result
        and "persisted" in result
        and result["nodes_visited"] >= 1
    )

    print("graph expansion v1 OK")
    print("nodes visited:", result.get("nodes_visited", 0))
    print("new ASINs:", result.get("new_asins", 0))
    print("deduped:", result.get("deduped", 0))
    print("persisted:", result.get("persisted", 0))

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
