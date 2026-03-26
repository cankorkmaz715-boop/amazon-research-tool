"""
Amazon product detail page parser. Extracts price, BSR, rating, review count.
Selector hardening: fallback selectors per field; never crash on missing/failed selectors.
Supports EN and DE (amazon.de) formats: European decimal/thousands separators,
"von 5 Sternen" ratings, parenthesised review counts, DE BSR selectors.
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
    # amazon.de – detail bullets (most common DE layout)
    "#detailBullets_feature_div",
    "#detailBulletsWrapper_feature_div",
    "#productDetails_detailBullets_sections1",
    # amazon.de – additional info table
    "#productDetails_db_sections",
    "#productDetails_techSpec_section_1",
    # generic / legacy
    "#SalesRank",
    "[data-feature-name='detailBullets']",
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

# --- Regex patterns (EN + DE) ---

# Rating: "4.8 out of 5" (EN) | "4,8 von 5 Sternen" (DE)
_RATING_RE = re.compile(
    r"([\d][.,][\d]|[\d]+)\s*(?:out of|von)\s*5",
    re.I,
)

# Review count:
#   EN: "2,662 ratings"  |  "1.234 Bewertungen"  (DE with dot thousands sep)
#   DE: "(2.662)"  |  "(2,662)"  – parenthesised, no keyword
_REVIEW_COUNT_RE = re.compile(
    r"[\(\[]?([\d][.,\d]*[\d]|[\d]+)[\)\]]?\s*"
    r"(?:ratings?|reviews?|Bewertungen?|Rezensionen?)?",
    re.I,
)


def _parse_price(text: Optional[str]) -> Optional[float]:
    """
    Extract numeric price handling both EN (1,234.56) and DE (1.234,56) formats.

    Detection logic:
    - If both ',' and '.' present: whichever comes last is the decimal separator.
    - If only ',' present and it splits into exactly 2 digits → decimal (DE: 23,36).
    - If only ',' present and right part has 3 digits → thousands sep (EN: 1,234).
    - If only '.' present and right part has 3 digits → thousands sep (DE: 1.234).
    - If only '.' present otherwise → decimal (EN: 19.99).
    """
    if not text:
        return None
    # Strip everything except digits, comma, dot
    cleaned = re.sub(r"[^\d.,]", "", text.strip())
    if not cleaned:
        return None

    last_comma = cleaned.rfind(",")
    last_dot   = cleaned.rfind(".")

    try:
        if last_comma > 0 and last_dot > 0:
            # Both separators present – last one is decimal
            if last_comma > last_dot:
                # DE format: 1.234,56
                normalized = cleaned.replace(".", "").replace(",", ".")
            else:
                # EN format: 1,234.56
                normalized = cleaned.replace(",", "")
        elif last_comma > 0:
            after_comma = cleaned[last_comma + 1:]
            if len(after_comma) == 3:
                # Thousands separator: 1,234
                normalized = cleaned.replace(",", "")
            else:
                # Decimal separator: 23,36
                normalized = cleaned.replace(",", ".")
        elif last_dot > 0:
            after_dot = cleaned[last_dot + 1:]
            if len(after_dot) == 3 and cleaned.count(".") == 1 and cleaned.index(".") > 0:
                # DE thousands separator: 1.234
                normalized = cleaned.replace(".", "")
            else:
                # EN decimal: 19.99
                normalized = cleaned
        else:
            normalized = cleaned

        return float(normalized) if normalized else None
    except ValueError:
        return None


def _parse_currency(text: Optional[str], market: Optional[str] = None) -> Optional[str]:
    """
    Extract currency from price string, with market fallback.
    Order matters: check A$ before $ to avoid AUD being classified as USD.
    """
    if not text:
        return _currency_from_market(market)
    if "A$" in text or "AU$" in text:
        return "AUD"
    if "€" in text:
        return "EUR"
    if "£" in text:
        return "GBP"
    if "$" in text:
        # Disambiguate USD vs AUD via market when symbol alone is ambiguous
        if market and market.upper() == "AU":
            return "AUD"
        return "USD"
    return _currency_from_market(market)


def _currency_from_market(market: Optional[str]) -> Optional[str]:
    """Return expected currency for a market code. Used as fallback when symbol not found."""
    if not market:
        return None
    try:
        from amazon_research.market.config import get_market_config
        cfg = get_market_config(market)
        return (cfg or {}).get("currency")
    except Exception:
        return None


def _parse_rating(text: Optional[str]) -> Optional[float]:
    """
    Parse rating from EN ('4.8 out of 5') or DE ('4,8 von 5 Sternen') format.
    Returns float 0.0–5.0 or None.
    """
    if not text:
        return None
    m = _RATING_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _parse_review_count(text: Optional[str]) -> Optional[int]:
    """
    Parse review count from EN ('2,662 ratings'), DE ('2.662 Bewertungen'),
    or parenthesised DE format ('(2.662)').
    Returns int or None.
    """
    if not text:
        return None
    m = _REVIEW_COUNT_RE.search(text.strip())
    if not m:
        return None
    raw = m.group(1)
    # Remove thousands separators (both ',' and '.')
    normalized = raw.replace(",", "").replace(".", "")
    try:
        val = int(normalized)
        return val if val > 0 else None
    except ValueError:
        return None


def _parse_bsr(raw: str) -> Optional[str]:
    """
    Extract BSR line from a text block.
    Matches EN ('Best Seller Rank', 'Sales Rank', '#') and
    DE ('Bestseller-Rang', 'Amazon Bestseller-Rang', 'Nr.').
    When keyword and rank number are on separate lines (common in DE detail bullets),
    the following non-empty line is returned instead.
    """
    if not raw:
        return None
    keywords = ("best seller", "sales rank", "bestseller", "amazon bestseller", "nr.")
    rank_re = re.compile(r"#[\d.,]|nr\.\s*\d", re.I)
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    for i, line in enumerate(lines):
        lower = line.lower()
        # Line contains keyword AND a rank number → return directly
        if any(kw in lower for kw in keywords) and rank_re.search(line):
            return line[:500]
        # Line contains keyword only → check next line for the rank
        if any(kw in lower for kw in keywords):
            if i + 1 < len(lines) and rank_re.search(lines[i + 1]):
                return lines[i + 1][:500]
        # Line starts with '#' (rank itself, no keyword needed)
        if line.startswith("#") and re.match(r"#[\d.,]+", line):
            return line[:500]
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


def extract_metrics_from_product_page(page, market: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract price, BSR, rating, review_count from current Amazon product page.
    Uses fallback selectors per field. Missing fields omitted. Never crashes.
    Supports EN (US/AU/UK) and DE (amazon.de/fr/it/es) page formats.
    Pass market code (e.g. 'DE', 'US', 'AU') for accurate currency fallback.
    """
    out: Dict[str, Any] = {}
    if market:
        out["market"] = market.upper()
    try:
        # Price
        try:
            raw = _first_text_from_selectors(page, SELECTORS_PRICE)
            if raw:
                price = _parse_price(raw)
                if price is not None:
                    out["price"] = price
                    out["currency"] = _parse_currency(raw, market) or "USD"
        except Exception:
            pass

        # BSR
        try:
            for sel in SELECTORS_BSR:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        raw = (loc.first.text_content() or "").strip()
                        bsr = _parse_bsr(raw)
                        if bsr:
                            out["bsr"] = bsr
                            break
                except Exception:
                    continue
        except Exception:
            pass

        # Rating
        try:
            raw = _first_text_from_selectors(page, SELECTORS_RATING)
            if raw:
                rating = _parse_rating(raw)
                if rating is not None:
                    out["rating"] = rating
        except Exception:
            pass

        # Review count
        try:
            raw = _first_text_from_selectors(page, SELECTORS_REVIEW_COUNT)
            if raw:
                review_count = _parse_review_count(raw)
                if review_count is not None:
                    out["review_count"] = review_count
        except Exception:
            pass

    except Exception as e:
        logger.warning("extract_metrics_from_product_page failed: %s", e)
        return {}

    if out:
        logger.info("product parser extracted metrics", extra={"keys": list(out.keys())})
    return out
