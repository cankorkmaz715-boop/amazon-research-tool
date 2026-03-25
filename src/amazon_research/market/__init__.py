"""
Multi-market foundation. Step 47 – market-aware URL building and config. DE default; extensible for UK, FR, IT, ES, US.
Step 109: Multi-marketplace engine v2 – resolve_market, get_domain, build_market_context for execution-aware flows.
"""
from .config import (
    get_default_market,
    get_listing_base_url,
    get_market_config,
    get_product_base_url,
    get_product_url,
    get_search_url,
    resolve_market,
    get_domain,
    build_market_context,
    SUPPORTED_MARKETS,
    PRODUCTION_MARKETS,
)

__all__ = [
    "SUPPORTED_MARKETS",
    "PRODUCTION_MARKETS",
    "get_default_market",
    "get_listing_base_url",
    "get_market_config",
    "get_product_base_url",
    "get_product_url",
    "get_search_url",
    "resolve_market",
    "get_domain",
    "build_market_context",
    "PRODUCTION_MARKETS",
]
