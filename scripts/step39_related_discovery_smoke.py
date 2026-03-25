#!/usr/bin/env python3
"""Step 39: Related/sponsored discovery hooks – extraction and graph persistence."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_connection, upsert_asin, get_asin_id, persist_related_sponsored_candidates, list_relationships
    from amazon_research.parsers.related_sponsored import extract_related_sponsored_from_html

    init_db()

    # Ensure asin_relationships table exists (Step 38)
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

    fixture_path = os.path.join(ROOT, "scripts", "fixtures", "sample_related_sponsored.html")
    with open(fixture_path, "r") as f:
        html = f.read()

    # Candidate extraction: must return related and sponsored with correct source_type
    candidates = extract_related_sponsored_from_html(html, max_related=5, max_sponsored=5)
    related = [c for c in candidates if c.get("source_type") == "related"]
    sponsored = [c for c in candidates if c.get("source_type") == "sponsored"]
    candidate_ok = len(related) >= 1 and len(sponsored) >= 1 and all("asin" in c for c in candidates)

    # Source labels: each candidate has source_type
    source_labels_ok = all(c.get("source_type") in ("related", "sponsored") for c in candidates)

    # Graph persistence: persist candidates from a "current" ASIN and verify edges
    from_id = upsert_asin("STEP39SOURCE", title="Step39 source")
    n = persist_related_sponsored_candidates(from_id, candidates)
    out_edges = list_relationships(asin_id=from_id, direction="out")
    by_type = {}
    for e in out_edges:
        by_type.setdefault(e["source_type"], []).append(e)
    graph_ok = n >= 1 and ("related" in by_type or "sponsored" in by_type)

    print("related discovery hooks OK")
    print("candidate extraction: OK" if candidate_ok else "candidate extraction: FAIL")
    print("source labels: OK" if source_labels_ok else "source labels: FAIL")
    print("graph persistence: OK" if graph_ok else "graph persistence: FAIL")

    if not (candidate_ok and source_labels_ok and graph_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
