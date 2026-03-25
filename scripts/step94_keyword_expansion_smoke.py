#!/usr/bin/env python3
"""Step 94: Keyword expansion engine – base keyword input, expansion, context signals, scanner compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.keywords import expand_keywords

    # --- Base keyword input: accepts base and returns structured result ---
    out = expand_keywords("mouse", use_db=False)
    base_ok = (
        out.get("base_keyword") == "mouse"
        and "candidates" in out
        and "summary" in out
    )

    # --- Keyword expansion: at least one expanded candidate ---
    candidates = out.get("candidates") or []
    expansion_ok = (
        isinstance(candidates, list)
        and len(candidates) >= 1
        and all(
            c.get("base_keyword") == "mouse"
            and c.get("expanded_keyword")
            and c.get("expanded_keyword") != "mouse"
            for c in candidates
        )
    )

    # --- Context signals: each candidate has context_signal ---
    signals_ok = all(
        "context_signal" in c and isinstance(c["context_signal"], str)
        for c in candidates
    )

    # --- Scanner compatibility: expanded_keyword is a string usable by scan_keyword ---
    scanner_ok = all(
        isinstance(c.get("expanded_keyword"), str) and len(c.get("expanded_keyword", "")) > 0
        for c in candidates
    ) if candidates else True

    print("keyword expansion engine OK")
    print("base keyword input: OK" if base_ok else "base keyword input: FAIL")
    print("keyword expansion: OK" if expansion_ok else "keyword expansion: FAIL")
    print("context signals: OK" if signals_ok else "context signals: FAIL")
    print("scanner compatibility: OK" if scanner_ok else "scanner compatibility: FAIL")

    if not (base_ok and expansion_ok and signals_ok and scanner_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
