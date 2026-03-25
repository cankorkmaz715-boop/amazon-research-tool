"""
Parsers – isolated selectors and extraction logic for listing and product pages.
"""

from .listing import extract_asins_from_amazon_listing
from .product import extract_metrics_from_product_page

__all__ = ["extract_asins_from_amazon_listing", "extract_metrics_from_product_page"]
