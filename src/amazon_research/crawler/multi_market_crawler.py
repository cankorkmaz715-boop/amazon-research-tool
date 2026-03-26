"""
Multi-market concurrent crawler.
Scrapes the same ASIN (or keyword search) across DE, US, AU simultaneously
using a ThreadPoolExecutor — one BrowserSession + proxy connection per market.

Usage:
    from amazon_research.crawler.multi_market_crawler import scrape_asin_multi_market
    results = scrape_asin_multi_market("B095DXC416", markets=["DE", "US", "AU"])
    for r in results:
        print(r["market"], r["metrics"])
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.market.config import get_product_url, get_search_url, PRODUCTION_MARKETS

logger = get_logger("crawler.multi_market")

# Per-thread timeout so one slow market doesn't block the others
_SCRAPE_TIMEOUT_SEC = 60


def _scrape_single_market(
    asin: Optional[str],
    market: str,
    keyword: Optional[str] = None,
    wait_sec: float = 3.0,
) -> Dict[str, Any]:
    """
    Open one BrowserSession for `market`, navigate to the ASIN product page (or
    keyword search page when keyword is given), parse metrics, return result dict.
    Always returns a dict with at least: market, status, elapsed_ms.
    """
    t0 = time.time()
    market = market.upper()
    result: Dict[str, Any] = {
        "market": market,
        "asin": asin,
        "status": "error",
        "metrics": {},
        "elapsed_ms": 0,
        "error": None,
    }

    try:
        from amazon_research.browser.automation import BrowserSession
        from amazon_research.detection.captcha import is_captcha_or_bot_check
        from amazon_research.parsers.product import extract_metrics_from_product_page
        from amazon_research.parsers.listing import extract_asins_from_amazon_listing

        if keyword:
            url = get_search_url(keyword, market)
        elif asin:
            url = get_product_url(asin, market)
        else:
            result["error"] = "asin or keyword required"
            return result

        result["url"] = url

        with BrowserSession(headless=True) as session:
            page = session.get_page()
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(wait_sec)

            if is_captcha_or_bot_check(page):
                result["status"] = "captcha"
                result["error"] = "captcha_or_block detected"
                return result

            if keyword:
                asins = extract_asins_from_amazon_listing(page)
                result["status"] = "ok"
                result["asins"] = [a["asin"] for a in asins]
                result["asin_count"] = len(asins)
            else:
                metrics = extract_metrics_from_product_page(page, market=market)
                result["status"] = "ok"
                result["metrics"] = metrics

    except Exception as e:
        result["error"] = str(e)
        logger.warning("multi_market scrape failed market=%s asin=%s: %s", market, asin, e)
    finally:
        result["elapsed_ms"] = round((time.time() - t0) * 1000)

    return result


def scrape_asin_multi_market(
    asin: str,
    markets: Optional[List[str]] = None,
    wait_sec: float = 3.0,
) -> List[Dict[str, Any]]:
    """
    Scrape one ASIN across multiple markets concurrently.
    Returns list of per-market result dicts (market, status, metrics, elapsed_ms).
    Markets default to PRODUCTION_MARKETS (DE, US, AU).
    """
    markets = [m.upper() for m in (markets or PRODUCTION_MARKETS)]
    results: List[Dict[str, Any]] = []

    logger.info("multi_market scrape start", extra={"asin": asin, "markets": markets})

    with ThreadPoolExecutor(max_workers=len(markets)) as pool:
        futures = {
            pool.submit(_scrape_single_market, asin, market, None, wait_sec): market
            for market in markets
        }
        for future in as_completed(futures, timeout=_SCRAPE_TIMEOUT_SEC):
            market = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                results.append({
                    "market": market,
                    "asin": asin,
                    "status": "error",
                    "metrics": {},
                    "elapsed_ms": 0,
                    "error": str(e),
                })

    results.sort(key=lambda r: r.get("market", ""))
    logger.info(
        "multi_market scrape done",
        extra={"asin": asin, "ok": sum(1 for r in results if r["status"] == "ok")},
    )
    return results


def scrape_keyword_multi_market(
    keyword: str,
    markets: Optional[List[str]] = None,
    wait_sec: float = 3.0,
) -> List[Dict[str, Any]]:
    """
    Search a keyword across multiple markets concurrently.
    Returns list of per-market result dicts (market, status, asins, asin_count, elapsed_ms).
    Markets default to PRODUCTION_MARKETS (DE, US, AU).
    """
    markets = [m.upper() for m in (markets or PRODUCTION_MARKETS)]
    results: List[Dict[str, Any]] = []

    logger.info("multi_market keyword search start", extra={"keyword": keyword, "markets": markets})

    with ThreadPoolExecutor(max_workers=len(markets)) as pool:
        futures = {
            pool.submit(_scrape_single_market, None, market, keyword, wait_sec): market
            for market in markets
        }
        for future in as_completed(futures, timeout=_SCRAPE_TIMEOUT_SEC):
            market = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                results.append({
                    "market": market,
                    "keyword": keyword,
                    "status": "error",
                    "asins": [],
                    "asin_count": 0,
                    "elapsed_ms": 0,
                    "error": str(e),
                })

    results.sort(key=lambda r: r.get("market", ""))
    logger.info(
        "multi_market keyword done",
        extra={"keyword": keyword, "ok": sum(1 for r in results if r["status"] == "ok")},
    )
    return results
