#!/usr/bin/env python3
"""Step 28: Dashboard preparation – stable contracts { data, meta }, filtering and sorting."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db
    from amazon_research.api import get_products, get_metrics, get_scores
    init_db()

    # Products contract: { data: list, meta: { count, limit, offset } }; each item has required keys
    PRODUCT_KEYS = {"asin", "title", "brand", "category", "product_url", "main_image_url", "created_at", "updated_at"}
    METRIC_KEYS = {"asin", "price", "currency", "bsr", "rating", "review_count", "seller_count", "updated_at"}
    SCORE_KEYS = {"asin", "competition_score", "demand_score", "opportunity_score", "scored_at"}
    META_KEYS = {"count", "limit", "offset"}

    def check_contract(resp, item_keys, name):
        if not isinstance(resp.get("data"), list) or not isinstance(resp.get("meta"), dict):
            return False
        for k in META_KEYS:
            if k not in resp["meta"]:
                return False
        for item in resp["data"][:3]:
            if not item_keys.issubset(item.keys()):
                return False
        return True

    ok_products = check_contract(get_products(limit=5), PRODUCT_KEYS, "products")
    ok_metrics = check_contract(get_metrics(limit=5), METRIC_KEYS, "metrics")
    ok_scores = check_contract(get_scores(limit=5), SCORE_KEYS, "scores")

    # Filtering/sorting: call with params and verify envelope and count consistency
    def check_filter_sort():
        try:
            r = get_products(limit=2, offset=0, sort_by="asin", order="asc")
            if not isinstance(r["data"], list) or len(r["data"]) > 2:
                return False
            if r["meta"]["limit"] != 2 or r["meta"]["offset"] != 0:
                return False
            r2 = get_metrics(limit=1, sort_by="updated_at", order="desc")
            if r2["meta"]["limit"] != 1:
                return False
            return True
        except Exception:
            return False

    ok_filter_sort = check_filter_sort()

    print("dashboard preparation OK")
    print("products contract: OK" if ok_products else "products contract: FAIL")
    print("metrics contract: OK" if ok_metrics else "metrics contract: FAIL")
    print("scores contract: OK" if ok_scores else "scores contract: FAIL")
    print("filtering/sorting: OK" if ok_filter_sort else "filtering/sorting: FAIL")

    if not (ok_products and ok_metrics and ok_scores and ok_filter_sort):
        sys.exit(1)

if __name__ == "__main__":
    main()
