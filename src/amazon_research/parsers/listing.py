"""
Amazon listing/category/search page parser. Extracts ASINs from visible product cards only.
Selector hardening: fallback selectors; never crash on missing/failed selectors.
"""
import re
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("parsers.listing")

# Fallback selectors – try in order. Add more as Amazon changes.
SELECTORS_DP_LINKS: List[str] = [
    'a[href*="/dp/"]',
    'a[href*="/gp/product/"]',
]
SELECTORS_DATA_ASIN: List[str] = [
    '[data-asin]',
    '[data-asin]:not([data-asin=""])',
    '.s-result-item[data-asin]',
]
# ASIN: 10 alphanumeric
_ASIN_RE = re.compile(r"^[A-Z0-9]{10}$", re.I)
_DP_ASIN_RE = re.compile(r"/dp/([A-Z0-9]{10})", re.I)
_GP_PRODUCT_RE = re.compile(r"/gp/product/([A-Z0-9]{10})", re.I)


def _extract_asins_from_hrefs(hrefs: List[str], seen: set) -> List[Dict[str, Any]]:
    """Parse ASINs from href list; skip duplicates. Never raises."""
    items: List[Dict[str, Any]] = []
    for href in (hrefs or []):
        try:
            match = _DP_ASIN_RE.search(href) or _GP_PRODUCT_RE.search(href)
            if match:
                asin = match.group(1).upper()
                if asin not in seen and _ASIN_RE.match(asin):
                    seen.add(asin)
                    items.append({"asin": asin})
        except Exception:
            continue
    return items


def extract_asins_from_amazon_listing(page) -> List[Dict[str, Any]]:
    """
    Extract ASINs from current Amazon listing/search page. Visible product cards only.
    Uses fallback selectors. Returns [] on any error. Never crashes.
    """
    items: List[Dict[str, Any]] = []
    seen: set = set()

    try:
        # 1) From product links – try each selector
        for sel in SELECTORS_DP_LINKS:
            try:
                hrefs = page.evaluate(f"""() => {{
                    const links = document.querySelectorAll('{sel}');
                    return Array.from(links).map(a => a.href).filter(Boolean);
                }}""")
                items.extend(_extract_asins_from_hrefs(hrefs or [], seen))
            except Exception:
                continue

        # 2) From data-asin – try each selector
        for sel in SELECTORS_DATA_ASIN:
            try:
                asin_attrs = page.evaluate(f"""() => {{
                    const nodes = document.querySelectorAll('{sel}');
                    return Array.from(nodes).map(el => el.getAttribute('data-asin')).filter(Boolean);
                }}""")
                for raw in (asin_attrs or []):
                    try:
                        asin = (raw or "").strip().upper()
                        if len(asin) == 10 and _ASIN_RE.match(asin) and asin not in seen:
                            seen.add(asin)
                            items.append({"asin": asin})
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception as e:
        logger.warning("extract_asins_from_amazon_listing failed: %s", e)
        return []

    logger.info("listing parser extracted ASINs", extra={"count": len(items)})
    return items
