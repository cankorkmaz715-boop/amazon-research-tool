"""
Related / sponsored product extraction from product pages. Step 39.
Extracts ASIN candidates from related/similar/sponsored sections; low-volume, source-labeled.
"""
import re
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("parsers.related_sponsored")

_DP_ASIN_RE = re.compile(r"/dp/([A-Z0-9]{10})", re.I)
# Fixture / test: sections marked with data-related-sponsored="related" or "sponsored"
# Match content of each section block (from opening tag to next section or end)
_SECTION_BLOCK_RE = re.compile(
    r'data-related-sponsored\s*=\s*["\'](related|sponsored)["\'][^>]*>(.*?)(?=data-related-sponsored\s*=|\Z)',
    re.I | re.DOTALL,
)


def extract_related_sponsored_from_html(
    html: str,
    max_related: int = 5,
    max_sponsored: int = 5,
) -> List[Dict[str, Any]]:
    """
    Extract ASINs from related and sponsored sections in HTML. Low-volume, capped.
    Looks for data-related-sponsored="related" and data-related-sponsored="sponsored" containers,
    then /dp/ASIN links within each block. Returns list of {"asin": str, "source_type": "related"|"sponsored"}.
    """
    out: List[Dict[str, Any]] = []
    seen: set = set()

    def collect_in_section(segment: str, source_type: str, cap: int) -> None:
        for match in _DP_ASIN_RE.finditer(segment):
            if len([x for x in out if x["source_type"] == source_type]) >= cap:
                break
            asin = match.group(1).upper()
            key = (asin, source_type)
            if key not in seen:
                seen.add(key)
                out.append({"asin": asin, "source_type": source_type})

    if not html or (max_related <= 0 and max_sponsored <= 0):
        return out

    for m in _SECTION_BLOCK_RE.finditer(html):
        source_type = m.group(1).lower()
        block = m.group(2)
        cap = max_related if source_type == "related" else max_sponsored
        if cap <= 0:
            continue
        collect_in_section(block, source_type, cap)

    return out


def extract_related_sponsored_candidates(page, max_related: int = 5, max_sponsored: int = 5) -> List[Dict[str, Any]]:
    """
    Extract related/sponsored ASIN candidates from current Playwright product page.
    Returns list of {"asin": str, "source_type": "related"|"sponsored"}. Never raises; returns [] on error.
    """
    try:
        html = page.content()
    except Exception as e:
        logger.warning("extract_related_sponsored_candidates: page.content failed: %s", e)
        return []
    return extract_related_sponsored_from_html(html, max_related=max_related, max_sponsored=max_sponsored)
