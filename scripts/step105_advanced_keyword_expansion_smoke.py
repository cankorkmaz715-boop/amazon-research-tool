#!/usr/bin/env python3
"""Step 105: Advanced keyword expansion – quality, signal aggregation, context enrichment, scanner compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.keywords import expand_keywords

    quality_ok = False
    signal_agg_ok = False
    context_ok = False
    scanner_ok = False

    # Baseline: expand without DB (modifier + context/title if provided)
    out = expand_keywords(
        "mouse",
        context_keywords=["wireless mouse", "gaming mouse"],
        title_tokens=["usb", "bluetooth"],
        use_db=False,
        max_candidates=25,
    )
    candidates = out.get("candidates") or []
    summary = out.get("summary") or {}

    # Quality: base_keyword, expanded_keyword, at least one candidate, structure
    quality_ok = (
        out.get("base_keyword") == "mouse"
        and isinstance(candidates, list)
        and len(candidates) >= 1
        and all(
            c.get("base_keyword") == "mouse"
            and c.get("expanded_keyword")
            and c.get("expanded_keyword") != "mouse"
            for c in candidates
        )
    )

    # Signal aggregation: expansion_signal_summary and/or context_signal; summary.by_signal when present
    signal_agg_ok = all(
        (("expansion_signal_summary" in c and isinstance(c.get("expansion_signal_summary"), dict)) or ("context_signal" in c))
        for c in candidates
    ) if candidates else True
    if summary.get("by_signal"):
        signal_agg_ok = signal_agg_ok and isinstance(summary["by_signal"], dict)

    # Context enrichment: confidence present; optional category/signal detail in expansion_signal_summary
    context_ok = all(
        c.get("confidence") in ("high", "medium", "low")
        for c in candidates
    ) if candidates else True

    # Scanner compatibility: expanded_keyword is non-empty string (scan_keyword(expanded_keyword))
    scanner_ok = all(
        isinstance(c.get("expanded_keyword"), str) and len(c.get("expanded_keyword", "").strip()) > 0
        for c in candidates
    ) if candidates else True

    print("advanced keyword expansion OK")
    print("keyword expansion quality: OK" if quality_ok else "keyword expansion quality: FAIL")
    print("signal aggregation: OK" if signal_agg_ok else "signal aggregation: FAIL")
    print("context enrichment: OK" if context_ok else "context enrichment: FAIL")
    print("scanner compatibility: OK" if scanner_ok else "scanner compatibility: FAIL")

    if not (quality_ok and signal_agg_ok and context_ok and scanner_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
