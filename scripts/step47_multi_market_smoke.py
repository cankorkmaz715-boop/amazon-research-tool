#!/usr/bin/env python3
"""Step 47: Multi-market foundation – default DE, market config, URL builder, market-aware routing."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.config import get_config
    from amazon_research.market import (
        SUPPORTED_MARKETS,
        get_default_market,
        get_market_config,
        get_product_base_url,
        get_product_url,
        get_listing_base_url,
    )

    # Default market: DE
    default = get_default_market()
    default_ok = default == "DE"

    # Market config: DE and UK have expected domains
    cfg_de = get_market_config("DE")
    cfg_uk = get_market_config("UK")
    config_ok = (
        cfg_de is not None
        and cfg_de.get("domain") == "www.amazon.de"
        and cfg_uk is not None
        and cfg_uk.get("domain") == "www.amazon.co.uk"
        and "DE" in SUPPORTED_MARKETS
        and "UK" in SUPPORTED_MARKETS
    )

    # URL builder: product base and full URL for DE
    base_de = get_product_base_url("DE")
    url_de = get_product_url("B001TEST01", "DE")
    url_builder_ok = (
        "amazon.de" in base_de
        and "/dp/" in base_de
        and "amazon.de" in url_de
        and "B001TEST01" in url_de
    )

    # Market-aware routing: listing base URL and refresh uses market URL
    listing_de = get_listing_base_url("DE")
    listing_uk = get_listing_base_url("UK")
    routing_ok = (
        "amazon.de" in listing_de
        and "/s" in listing_de
        and "amazon.co.uk" in listing_uk
    )
    base_default = get_product_base_url()
    routing_ok = routing_ok and "amazon.de" in base_default

    print("multi-market foundation OK")
    print("default market: OK" if default_ok else "default market: FAIL")
    print("market config: OK" if config_ok else "market config: FAIL")
    print("url builder: OK" if url_builder_ok else "url builder: FAIL")
    print("market-aware routing: OK" if routing_ok else "market-aware routing: FAIL")

    if not (default_ok and config_ok and url_builder_ok and routing_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
