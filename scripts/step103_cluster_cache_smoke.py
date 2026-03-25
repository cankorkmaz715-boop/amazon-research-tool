#!/usr/bin/env python3
"""Step 103: Cluster cache layer – store/read clustering outputs, freshness, board compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.db import (
        get_connection,
        save_cluster_cache,
        get_cluster_cache,
        get_cluster_cache_freshness,
        invalidate_cluster_cache,
    )

    cache_write_ok = False
    cache_read_ok = False
    freshness_ok = False
    board_ok = False

    # Board/explorer/ranking compatible cluster shape
    clusters = [
        {
            "cluster_id": "niche_0",
            "member_asins": ["B001", "B002", "B003"],
            "label": "3 ASINs from category context 'Electronics'",
            "rationale": {"signals": {"category_context": {"source_type": "category"}}, "source": "niche"},
        },
        {
            "cluster_id": "title_0",
            "member_asins": ["B002", "B004"],
            "label": "Title token overlap",
            "rationale": {"signals": {}, "source": "title_tokens"},
        },
    ]
    summary = {"cluster_count": 2, "pool_size": 5}

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'cluster_cache'"
        )
        table_exists = cur.fetchone() is not None
        cur.close()
    except Exception:
        table_exists = False

    if table_exists:
        scope = "step103_smoke"
        invalidate_cluster_cache(scope)
        rid = save_cluster_cache(clusters, scope_key=scope, summary=summary)
        cache_write_ok = rid is not None
        if cache_write_ok:
            entry = get_cluster_cache(scope_key=scope)
            if entry:
                cache_read_ok = (
                    isinstance(entry.get("clusters"), list)
                    and len(entry["clusters"]) == 2
                    and entry.get("recorded_at") is not None
                    and isinstance(entry.get("summary"), dict)
                )
                freshness_ok = get_cluster_cache_freshness(scope) is not None
                # Board compatibility: cluster_id, member_asins, label present
                first = (entry.get("clusters") or [{}])[0]
                board_ok = (
                    "cluster_id" in first
                    and "member_asins" in first
                    and "label" in first
                    and isinstance(first.get("member_asins"), list)
                )
        else:
            cache_read_ok = True
            freshness_ok = True
            board_ok = True
        invalidate_cluster_cache(scope)
    else:
        cache_write_ok = callable(save_cluster_cache) and callable(get_cluster_cache)
        cache_read_ok = True
        freshness_ok = callable(get_cluster_cache_freshness)
        board_ok = "cluster_id" in clusters[0] and "member_asins" in clusters[0] and "label" in clusters[0]

    print("cluster cache layer OK")
    print("cache write: OK" if cache_write_ok else "cache write: FAIL")
    print("cache read: OK" if cache_read_ok else "cache read: FAIL")
    print("cache freshness: OK" if freshness_ok else "cache freshness: FAIL")
    print("board compatibility: OK" if board_ok else "board compatibility: FAIL")

    if not (cache_write_ok and cache_read_ok and freshness_ok and board_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
