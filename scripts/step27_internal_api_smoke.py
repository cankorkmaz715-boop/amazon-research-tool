#!/usr/bin/env python3
"""Step 27: Internal API v1 – read-only /products, /metrics, /scores. Verifies endpoints respond OK."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db
    init_db()

    # Import handler logic to call without starting server (avoids port binding in tests)
    from amazon_research.api import get_products, get_metrics, get_scores

    def check_products():
        try:
            r = get_products()
            return isinstance(r.get("data"), list) and isinstance(r.get("meta"), dict)
        except Exception:
            return False

    def check_metrics():
        try:
            r = get_metrics()
            return isinstance(r.get("data"), list) and isinstance(r.get("meta"), dict)
        except Exception:
            return False

    def check_scores():
        try:
            r = get_scores()
            return isinstance(r.get("data"), list) and isinstance(r.get("meta"), dict)
        except Exception:
            return False

    ok_products = check_products()
    ok_metrics = check_metrics()
    ok_scores = check_scores()

    print("internal api v1 OK")
    print("/products endpoint: OK" if ok_products else "/products endpoint: FAIL")
    print("/metrics endpoint: OK" if ok_metrics else "/metrics endpoint: FAIL")
    print("/scores endpoint: OK" if ok_scores else "/scores endpoint: FAIL")

    if not (ok_products and ok_metrics and ok_scores):
        sys.exit(1)

if __name__ == "__main__":
    main()
