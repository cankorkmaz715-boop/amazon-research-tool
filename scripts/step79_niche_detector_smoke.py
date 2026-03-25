#!/usr/bin/env python3
"""Step 79: Niche detector foundation – candidate grouping, context signals, niche output structure."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.niche import detect_niches

    # --- Without DB: discovery context only (category + keyword signals) ---
    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = detect_niches(
        asin_pool,
        discovery_context=discovery_context,
        use_db=False,
    )

    # --- Candidate grouping: candidates with asin_set ---
    candidates = out.get("candidates") or []
    grouping_ok = isinstance(candidates, list) and all(
        isinstance(c, dict) and "asin_set" in c and isinstance(c["asin_set"], list)
        for c in candidates
    )

    # --- Context signals: category_context and keyword_context on candidates ---
    has_category = any(
        c.get("signals", {}).get("category_context") for c in candidates
    )
    has_keyword = any(
        c.get("signals", {}).get("keyword_context") for c in candidates
    )
    signals_ok = has_category and has_keyword and all(
        "signals" in c and "explanation" in c for c in candidates
    )

    # --- Niche output structure: candidates + summary ---
    summary = out.get("summary") or {}
    structure_ok = (
        "candidates" in out
        and "summary" in out
        and isinstance(summary, dict)
        and "total_candidates" in summary
        and "pool_size" in summary
    )

    print("niche detector foundation OK")
    print("candidate grouping: OK" if grouping_ok else "candidate grouping: FAIL")
    print("context signals: OK" if signals_ok else "context signals: FAIL")
    print("niche output structure: OK" if structure_ok else "niche output structure: FAIL")

    if not (grouping_ok and signals_ok and structure_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
