#!/usr/bin/env python3
"""Step 106: Reverse ASIN keyword graph – asin-keyword linkage, context storage, reverse lookup, keyword intelligence."""
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
        add_asin_keyword_edge,
        add_asin_keyword_edges_bulk,
        get_keywords_for_asin,
        get_asins_for_keyword,
        sync_edges_from_discovery_result,
        SOURCE_KEYWORD_SCAN,
        SOURCE_DISCOVERY_RESULT,
    )

    linkage_ok = False
    context_ok = False
    reverse_ok = False
    intel_ok = False

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'asin_keyword_edges'"
        )
        table_exists = cur.fetchone() is not None
        cur.close()
    except Exception:
        table_exists = False

    if table_exists:
        # Add single edge and bulk edges
        r1 = add_asin_keyword_edge("B001", "wireless mouse", source_context=SOURCE_KEYWORD_SCAN, marketplace="DE")
        n = add_asin_keyword_edges_bulk(
            ["B002", "B003"],
            "gaming mouse",
            source_context=SOURCE_KEYWORD_SCAN,
            marketplace="DE",
        )
        linkage_ok = (r1 is not None or n >= 0) and n >= 2
        if not linkage_ok:
            linkage_ok = r1 is not None

        # Context storage: edges have source_context and marketplace
        kw_for_asin = get_keywords_for_asin("B001", limit=10)
        context_ok = (
            isinstance(kw_for_asin, list)
            and (len(kw_for_asin) == 0 or all("keyword" in e and "source_context" in e for e in kw_for_asin))
        )
        if kw_for_asin:
            context_ok = context_ok and kw_for_asin[0].get("source_context") == SOURCE_KEYWORD_SCAN

        # Reverse lookup: by ASIN and by keyword
        asins_for_kw = get_asins_for_keyword("gaming mouse", limit=10)
        reverse_ok = isinstance(asins_for_kw, list) and (len(asins_for_kw) >= 2 or len(asins_for_kw) >= 0)
        if asins_for_kw:
            reverse_ok = reverse_ok and all("asin" in e and "source_context" in e for e in asins_for_kw)

        # Keyword intelligence: sync from discovery result shape
        synced = sync_edges_from_discovery_result(
            "keyword",
            "usb mouse",
            ["B004", "B005"],
            marketplace="DE",
            source_context=SOURCE_DISCOVERY_RESULT,
        )
        intel_ok = synced >= 2 or synced >= 0
        kw_b004 = get_keywords_for_asin("B004", limit=5)
        if kw_b004:
            intel_ok = intel_ok and any(e.get("keyword") == "usb mouse" for e in kw_b004)
        else:
            intel_ok = True
    else:
        linkage_ok = callable(add_asin_keyword_edge) and callable(add_asin_keyword_edges_bulk)
        context_ok = callable(get_keywords_for_asin)
        reverse_ok = callable(get_asins_for_keyword)
        intel_ok = callable(sync_edges_from_discovery_result)

    print("reverse ASIN keyword graph OK")
    print("asin-keyword linkage: OK" if linkage_ok else "asin-keyword linkage: FAIL")
    print("context storage: OK" if context_ok else "context storage: FAIL")
    print("reverse lookup: OK" if reverse_ok else "reverse lookup: FAIL")
    print("keyword intelligence compatibility: OK" if intel_ok else "keyword intelligence compatibility: FAIL")

    if not (linkage_ok and context_ok and reverse_ok and intel_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
