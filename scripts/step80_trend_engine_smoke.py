#!/usr/bin/env python3
"""Step 80: Trend engine foundation – price, review, rating, rank trends and output structure."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def _has_trend_structure(d: dict) -> bool:
    return (
        isinstance(d, dict)
        and "trend" in d
        and "value_first" in d
        and "value_last" in d
        and "points" in d
        and "explanation" in d
    )


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.trend import (
        get_price_trend,
        get_review_count_trend,
        get_rating_trend,
        get_rank_trend,
        get_trends_for_asin,
    )

    # Use a fixed asin_id; with no DB or no history we still get valid structure (insufficient_data)
    asin_id = 1

    price = get_price_trend(asin_id)
    price_ok = _has_trend_structure(price) and price["trend"] in (
        "rising", "falling", "stable", "noisy", "insufficient_data"
    )

    review = get_review_count_trend(asin_id)
    review_ok = _has_trend_structure(review) and review["trend"] in (
        "rising", "falling", "stable", "noisy", "insufficient_data"
    )

    rating = get_rating_trend(asin_id)
    rating_ok = _has_trend_structure(rating) and rating["trend"] in (
        "rising", "falling", "stable", "noisy", "insufficient_data"
    )

    rank = get_rank_trend(asin_id)
    rank_ok = _has_trend_structure(rank) and rank["trend"] in (
        "rising", "falling", "stable", "noisy", "insufficient_data"
    )

    agg = get_trends_for_asin(asin_id)
    structure_ok = (
        isinstance(agg, dict)
        and agg.get("asin_id") == asin_id
        and "price" in agg
        and "review_count" in agg
        and "rating" in agg
        and "rank" in agg
        and _has_trend_structure(agg["price"])
        and _has_trend_structure(agg["review_count"])
        and _has_trend_structure(agg["rating"])
        and _has_trend_structure(agg["rank"])
    )

    print("trend engine foundation OK")
    print("price trend: OK" if price_ok else "price trend: FAIL")
    print("review trend: OK" if review_ok else "review trend: FAIL")
    print("rating trend: OK" if rating_ok else "rating trend: FAIL")
    print("rank trend: OK" if rank_ok else "rank trend: FAIL")
    print("trend output structure: OK" if structure_ok else "trend output structure: FAIL")

    if not (price_ok and review_ok and rating_ok and rank_ok and structure_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
