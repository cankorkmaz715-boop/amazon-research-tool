"""
Amazon product detail page parser. Extracts price, BSR, rating, review count.
Selector hardening: fallback selectors per field; never crash on missing/failed selectors.
"""
import re
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("parsers.product")

# Fallback selectors per field – try in order; first match wins. Add more as Amazon changes.
SELECTORS_PRICE: List[str] = [
    ".a-price .a-offscreen",
    "#corePrice_feature_div .a-offscreen",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    "#apex_offerDisplay_desktop .a-offscreen",
    ".a-price-whole",
    "[data-a-color='price'] .a-offscreen",
]
SELECTORS_BSR: List[str] = [
    "#productDetails_detailBullets_sections1",
    "#SalesRank",
    "[data-feature-name='detailBullets']",
    "#detailBulletsWrapper_feature_div",
    "table#productDetails_detailBullets_sections1",
]
SELECTORS_RATING: List[str] = [
    "#acrPopover span.a-icon-alt",
    ".a-icon-star-small span.a-icon-alt",
    "span[data-rating]",
    "#acrPopover .a-icon-alt",
    ".reviewCountTextLinkedHistogram + span",
]
SELECTORS_REVIEW_COUNT: List[str] = [
    "#acrCustomerReviewText",
    "#acrCustomerReviewLink",
    "#acrNumberOfReviews",
    "span#acrCustomerReviewText",
    "a#acrCustomerReviewLink",
]

_PRICE_RE = re.compile(r"[\d,]+\.?\d*")
_RATING_RE = re.compile(r"([\d.]+)\s*out of\s*5")
_REVIEW_COUNT_RE = re.compile(r"([\d,]+)\s*(?:ratings?|reviews?)", re.I)


def _parse_price(text: Optional[str]) -> Optional[float]:
    """Extract numeric price from string like '$19.99' or '1,234.56'."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,]", "", text.strip())
    match = _PRICE_RE.search(cleaned.replace(",", ""))
    if match:
        try:
            return float(match.group(0).replace(",", ""))
        except ValueError:
            pass
    return None


def _parse_currency(text: Optional[str]) -> Optional[str]:
    """Extract currency symbol or code from price string."""
    if not text:
        return None
    if "$" in text:
        return "USD"
    if "€" in text:
        return "EUR"
    if "£" in text:
        return "GBP"
    return None


def _first_text_from_selectors(page, selectors: List[str]) -> Optional[str]:
    """Try each selector; return first non-empty text_content(). Never raises."""
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                raw = loc.first.text_content()
                if raw and raw.strip():
                    return raw.strip()
        except Exception:
            continue
    return None


def extract_metrics_from_product_page(page) -> Dict[str, Any]:
    """
    Extract price, BSR, rating, review_count from current Amazon product page.
    Uses fallback selectors per field. Missing fields omitted. Never crashes.
    """
    out: Dict[str, Any] = {}
    try:
        # Price – try fallbacks until one parses
        try:
            raw = _first_text_from_selectors(page, SELECTORS_PRICE)
            if raw:
                price = _parse_price(raw)
                if price is not None:
                    out["price"] = price
                    out["currency"] = _parse_currency(raw) or "USD"
        except Exception:
            pass

        # BSR – try fallbacks, take first block containing rank text
        try:
            for sel in SELECTORS_BSR:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        raw = (loc.first.text_content() or "").strip()
                        if "best seller" in raw.lower() or "sales rank" in raw.lower() or "#" in raw:
                            for line in raw.split("\n"):
                                line = line.strip()
                                if line and ("#" in line or "rank" in line.lower()):
                                    out["bsr"] = line[:500]
                                    break
                        if out.get("bsr"):
                            break
                except Exception:
                    continue
        except Exception:
            pass

        # Rating – try fallbacks
        try:
            raw = _first_text_from_selectors(page, SELECTORS_RATING)
            if raw:
                match = _RATING_RE.search(raw)
                if match:
                    out["rating"] = float(match.group(1))
        except Exception:
            pass

        # Review count – try fallbacks
        try:
            raw = _first_text_from_selectors(page, SELECTORS_REVIEW_COUNT)
            if raw:
                match = _REVIEW_COUNT_RE.search(raw)
                if match:
                    out["review_count"] = int(match.group(1).replace(",", ""))
        except Exception:
            pass

    except Exception as e:
        logger.warning("extract_metrics_from_product_page failed: %s", e)
        return {}

    if out:
        logger.info("product parser extracted metrics", extra={"keys": list(out.keys())})
    return out
