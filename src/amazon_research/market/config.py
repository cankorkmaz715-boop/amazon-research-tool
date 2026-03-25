"""
Market config and URL building. Step 47 – DE default; extensible for UK, FR, IT, ES, US.
Step 75: get_search_url for keyword crawler. No scraping logic.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

# Supported marketplace codes and their domains. Product path /dp/ is standard across markets.
SUPPORTED_MARKETS: List[str] = ["DE", "UK", "US", "AU", "FR", "IT", "ES"]

# Step 184: Production markets for multi-market crawler activation (DE, US, AU). Conservative 24/7.
PRODUCTION_MARKETS: List[str] = ["DE", "US", "AU"]

_MARKET_CONFIG: Dict[str, Dict[str, Any]] = {
    "DE": {"domain": "www.amazon.de", "product_path": "/dp/", "listing_path": "/s", "locale": "de_DE"},
    "UK": {"domain": "www.amazon.co.uk", "product_path": "/dp/", "listing_path": "/s", "locale": "en_GB"},
    "US": {"domain": "www.amazon.com", "product_path": "/dp/", "listing_path": "/s", "locale": "en_US"},
    "AU": {"domain": "www.amazon.com.au", "product_path": "/dp/", "listing_path": "/s", "locale": "en_AU"},
    "FR": {"domain": "www.amazon.fr", "product_path": "/dp/", "listing_path": "/s", "locale": "fr_FR"},
    "IT": {"domain": "www.amazon.it", "product_path": "/dp/", "listing_path": "/s", "locale": "it_IT"},
    "ES": {"domain": "www.amazon.es", "product_path": "/dp/", "listing_path": "/s", "locale": "es_ES"},
}


def get_market_config(market_code: str) -> Optional[Dict[str, Any]]:
    """Return config dict for market code (domain, product_path, listing_path, locale) or None if unsupported."""
    code = (market_code or "").strip().upper()
    return _MARKET_CONFIG.get(code)


def get_product_base_url(market: Optional[str] = None) -> str:
    """Return product base URL (e.g. https://www.amazon.de/dp/) for market. Uses default_market if market is None."""
    from amazon_research.config import get_config
    code = (market or "").strip().upper() or (getattr(get_config(), "default_market", None) or "DE").strip().upper()
    cfg = get_market_config(code)
    if not cfg:
        return get_config().amazon_product_base_url
    return f"https://{cfg['domain']}{cfg['product_path']}"


def get_product_url(asin: str, market: Optional[str] = None) -> str:
    """Return full product URL for ASIN and market (default market if None)."""
    base = get_product_base_url(market)
    asin = (asin or "").strip()
    return f"{base}{asin}" if asin else base


def get_listing_base_url(market: Optional[str] = None) -> str:
    """Return listing/search base URL (e.g. https://www.amazon.de/s) for market. For discovery routing."""
    from amazon_research.config import get_config
    code = (market or "").strip().upper() or (getattr(get_config(), "default_market", None) or "DE").strip().upper()
    cfg = get_market_config(code)
    if not cfg:
        return "https://www.amazon.de/s"
    return f"https://{cfg['domain']}{cfg['listing_path']}"


def get_default_market() -> str:
    """Return default market code from config (e.g. DE)."""
    from amazon_research.config import get_config
    return (getattr(get_config(), "default_market", None) or "DE").strip().upper()


def get_search_url(keyword: str, market: Optional[str] = None) -> str:
    """Step 75: Return marketplace-specific Amazon search URL for the keyword (e.g. https://www.amazon.de/s?k=...)."""
    base = get_listing_base_url(market)
    q = quote_plus((keyword or "").strip())
    return f"{base}?k={q}" if q else base


def resolve_market(market: Optional[str] = None) -> str:
    """Step 109: Resolve to a supported market code. Returns DE when unknown or None. Execution-aware default."""
    code = (market or "").strip().upper()
    if not code:
        return get_default_market()
    return code if code in SUPPORTED_MARKETS else get_default_market()


def get_domain(market: Optional[str] = None) -> str:
    """Step 109: Return domain (e.g. www.amazon.de) for market. Uses resolve_market for default."""
    code = resolve_market(market)
    cfg = get_market_config(code)
    return cfg["domain"] if cfg else "www.amazon.de"


def build_market_context(market: Optional[str] = None) -> Dict[str, Any]:
    """
    Step 109: Build execution-aware market context for scanning and persistence.
    Returns dict: market_code, domain, product_base_url, listing_base_url, locale.
    Use for category/keyword scanning, discovery persistence, trend/history context.
    """
    code = resolve_market(market)
    cfg = get_market_config(code) or {}
    return {
        "market_code": code,
        "domain": cfg.get("domain", "www.amazon.de"),
        "product_base_url": get_product_base_url(code),
        "listing_base_url": get_listing_base_url(code),
        "locale": cfg.get("locale", "de_DE"),
    }
