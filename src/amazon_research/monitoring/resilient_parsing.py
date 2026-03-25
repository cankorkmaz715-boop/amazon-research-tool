"""
Step 169: Resilient parsing layer – tolerance to HTML/layout changes.
Selector fallback chains, partial extraction, field-level parse status, parser confidence.
Integrates with data quality guard, data integrity repair, scraper reliability.
Does not rewrite crawler/worker core. Lightweight, rule-based, extensible.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.resilient_parsing")

# Page/target types
PAGE_PRODUCT_CARD = "product_card"
PAGE_PRODUCT_DETAIL = "product_detail"
PAGE_LISTING = "listing_page"

# Field names we care about (product cards / detail)
FIELDS_PRODUCT = ["asin", "title", "price", "rating", "review_count", "rank", "bsr"]
FIELDS_REQUIRED_FOR_CARD = ["asin", "title"]
FIELDS_REQUIRED_FOR_DETAIL = ["asin", "title", "price"]

# Fallback chains: for each logical field, ordered list of keys to try (e.g. selector results)
SELECTOR_FALLBACK_CHAINS: Dict[str, List[str]] = {
    "asin": ["asin", "asin_id", "data-asin", "product_id"],
    "title": ["title", "product_title", "productTitle", "name"],
    "price": ["price", "price_primary", "a_price", "list_price", "price_amount"],
    "rating": ["rating", "average_rating", "stars", "review_rating"],
    "review_count": ["review_count", "reviewCount", "num_reviews", "reviews"],
    "rank": ["rank", "bsr_rank", "sales_rank"],
    "bsr": ["bsr", "best_seller_rank", "rank", "sales_rank"],
}

PARSE_STATUS_OK = "ok"
PARSE_STATUS_PARTIAL = "partial"
PARSE_STATUS_FAIL = "fail"
FIELD_STATUS_EXTRACTED = "extracted"
FIELD_STATUS_FALLBACK = "fallback"
FIELD_STATUS_MISSING = "missing"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def apply_selector_fallback(
    raw: Dict[str, Any],
    logical_field: str,
    fallback_chain: Optional[List[str]] = None,
) -> Tuple[Any, str]:
    """
    Try each key in the fallback chain; return (value, status).
    status: extracted (first key hit), fallback (later key), missing (none).
    """
    chain = fallback_chain or SELECTOR_FALLBACK_CHAINS.get(logical_field, [logical_field])
    for i, key in enumerate(chain):
        val = raw.get(key)
        if not _is_empty(val):
            status = FIELD_STATUS_EXTRACTED if i == 0 else FIELD_STATUS_FALLBACK
            return val, status
    return None, FIELD_STATUS_MISSING


def extract_with_fallback(
    raw: Dict[str, Any],
    fields: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Extract logical fields from raw using selector fallback chains.
    Returns dict: extracted_fields, missing_fields, field_level_status.
    """
    fields = fields or FIELDS_PRODUCT
    extracted: Dict[str, Any] = {}
    missing: List[str] = []
    field_status: Dict[str, str] = {}
    for f in fields:
        val, status = apply_selector_fallback(raw, f)
        if status != FIELD_STATUS_MISSING and val is not None:
            extracted[f] = val
            field_status[f] = status
        else:
            missing.append(f)
            field_status[f] = FIELD_STATUS_MISSING
    return {
        "extracted_fields": extracted,
        "missing_fields": missing,
        "field_level_status": field_status,
    }


def compute_parser_confidence(
    extracted_fields: Dict[str, Any],
    missing_fields: Sequence[str],
    field_level_status: Dict[str, str],
    required: Optional[Sequence[str]] = None,
) -> float:
    """
    Rule-based confidence in [0, 1]. Higher when more fields present and required fields present.
    Slight boost when fallback was used (we still got data).
    """
    required = required or FIELDS_REQUIRED_FOR_CARD
    total = len(extracted_fields) + len(missing_fields)
    if total == 0:
        return 0.0
    filled = len(extracted_fields)
    base = filled / total
    required_ok = sum(1 for r in required if r in extracted_fields) / max(1, len(required))
    # Blend: 60% coverage, 40% required
    conf = 0.6 * base + 0.4 * required_ok
    fallback_count = sum(1 for s in field_level_status.values() if s == FIELD_STATUS_FALLBACK)
    if fallback_count > 0 and filled > 0:
        conf = min(1.0, conf + 0.05)  # small boost for resilience
    return round(conf, 2)


def get_parse_health_summary(
    parser_confidence: float,
    missing_fields: Sequence[str],
) -> str:
    """Human-readable parse health: ok, partial, fail."""
    if parser_confidence >= 0.8 and len(missing_fields) <= 1:
        return PARSE_STATUS_OK
    if parser_confidence >= 0.4 or len(missing_fields) < len(FIELDS_PRODUCT):
        return PARSE_STATUS_PARTIAL
    return PARSE_STATUS_FAIL


def parse_resilient(
    raw: Dict[str, Any],
    target_id: str = "",
    page_type: str = PAGE_PRODUCT_CARD,
    fields: Optional[Sequence[str]] = None,
    required: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Full resilient parse: apply fallback extraction, compute confidence, produce structured output.
    Output: target_id, page_type, extracted_fields, missing_fields, parser_confidence, parse_status, timestamp.
    """
    target_id = (target_id or "").strip() or "unknown"
    if required is None:
        required = FIELDS_REQUIRED_FOR_CARD if page_type == PAGE_PRODUCT_CARD else FIELDS_REQUIRED_FOR_DETAIL
    out = extract_with_fallback(raw, fields=fields or FIELDS_PRODUCT)
    extracted = out["extracted_fields"]
    missing = out["missing_fields"]
    field_status = out["field_level_status"]
    confidence = compute_parser_confidence(extracted, missing, field_status, required=required)
    health = get_parse_health_summary(confidence, missing)
    return {
        "target_id": target_id,
        "page_type": page_type,
        "extracted_fields": extracted,
        "missing_fields": missing,
        "field_level_status": field_status,
        "parser_confidence": confidence,
        "parse_status": health,
        "timestamp": _now_iso(),
    }


def parse_product_card(raw: Dict[str, Any], target_id: str = "") -> Dict[str, Any]:
    """Convenience: parse as product card (listing item)."""
    return parse_resilient(raw, target_id=target_id, page_type=PAGE_PRODUCT_CARD, required=FIELDS_REQUIRED_FOR_CARD)


def parse_product_detail(raw: Dict[str, Any], target_id: str = "") -> Dict[str, Any]:
    """Convenience: parse as product detail page."""
    return parse_resilient(raw, target_id=target_id, page_type=PAGE_PRODUCT_DETAIL, required=FIELDS_REQUIRED_FOR_DETAIL)


def to_quality_guard_input(parse_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert resilient parse output to a record suitable for data_quality_guard.missing_data_check.
    Uses extracted_fields so the guard can run on normalized fields.
    """
    return dict(parse_result.get("extracted_fields") or {})


def run_quality_guard_on_parse(parse_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Run data quality guard missing_data_check on the parsed record.
    Integrates with data quality guard.
    """
    try:
        from amazon_research.monitoring.data_quality_guard import missing_data_check
        record = to_quality_guard_input(parse_result)
        return missing_data_check(record=record)
    except Exception as e:
        logger.debug("run_quality_guard_on_parse: %s", e)
        return []
