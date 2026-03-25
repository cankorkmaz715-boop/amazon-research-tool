#!/usr/bin/env python3
"""Step 169: Resilient parsing layer – selector fallback, partial extraction, parse confidence, quality guard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.monitoring.resilient_parsing import (
        apply_selector_fallback,
        extract_with_fallback,
        compute_parser_confidence,
        get_parse_health_summary,
        parse_resilient,
        parse_product_card,
        parse_product_detail,
        to_quality_guard_input,
        run_quality_guard_on_parse,
        FIELD_STATUS_EXTRACTED,
        FIELD_STATUS_FALLBACK,
        FIELD_STATUS_MISSING,
        PARSE_STATUS_OK,
        PARSE_STATUS_PARTIAL,
        PARSE_STATUS_FAIL,
    )

    # 1) Selector fallback: primary key missing, fallback key present
    raw_fallback = {"price_primary": 19.99, "title": "Widget"}
    val, status = apply_selector_fallback(raw_fallback, "price")
    fallback_ok = val == 19.99 and status == FIELD_STATUS_FALLBACK
    val2, status2 = apply_selector_fallback(raw_fallback, "title")
    fallback_ok = fallback_ok and val2 == "Widget" and status2 == FIELD_STATUS_EXTRACTED
    val3, status3 = apply_selector_fallback({"x": 1}, "asin")
    fallback_ok = fallback_ok and status3 == FIELD_STATUS_MISSING

    # 2) Partial extraction: some fields missing
    raw_partial = {"asin": "B001", "title": "Thing", "review_count": 100}
    out = extract_with_fallback(raw_partial)
    partial_ok = (
        out.get("extracted_fields", {}).get("asin") == "B001"
        and "price" in (out.get("missing_fields") or [])
        and "rating" in (out.get("missing_fields") or [])
        and isinstance(out.get("field_level_status"), dict)
    )

    # 3) Parse confidence and health
    extracted = {"asin": "B001", "title": "T", "price": 9.99}
    missing = ["rating", "review_count", "rank", "bsr"]
    field_status = {"asin": FIELD_STATUS_EXTRACTED, "title": FIELD_STATUS_EXTRACTED, "price": FIELD_STATUS_FALLBACK}
    conf = compute_parser_confidence(extracted, missing, field_status)
    confidence_ok = isinstance(conf, (int, float)) and 0 <= conf <= 1
    health = get_parse_health_summary(conf, missing)
    confidence_ok = confidence_ok and health in (PARSE_STATUS_OK, PARSE_STATUS_PARTIAL, PARSE_STATUS_FAIL)
    full = parse_resilient({"asin": "B002", "title": "Y", "price": 5.99}, target_id="card-1", page_type="product_card")
    confidence_ok = (
        confidence_ok
        and "parser_confidence" in full
        and "parse_status" in full
        and "extracted_fields" in full
        and "missing_fields" in full
        and "timestamp" in full
    )

    # 4) Quality guard compatibility
    rec = to_quality_guard_input(full)
    quality_ok = isinstance(rec, dict) and "asin" in rec and "title" in rec
    issues = run_quality_guard_on_parse(full)
    quality_ok = quality_ok and isinstance(issues, list)

    print("resilient parsing layer OK")
    print("selector fallback: OK" if fallback_ok else "selector fallback: FAIL")
    print("partial extraction: OK" if partial_ok else "partial extraction: FAIL")
    print("parse confidence: OK" if confidence_ok else "parse confidence: FAIL")
    print("quality guard compatibility: OK" if quality_ok else "quality guard compatibility: FAIL")

    if not (fallback_ok and partial_ok and confidence_ok and quality_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
