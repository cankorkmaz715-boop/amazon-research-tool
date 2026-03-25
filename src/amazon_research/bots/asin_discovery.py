"""
ASIN discovery bot – scans categories/listings, discovers new ASINs, stores via persistence layer.
Multi-Page v2: up to 2–3 pages (capped), conservative navigation, stop on error, dedupe across pages.
"""
import re
import time
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.browser import BrowserSession
from amazon_research.db import get_enabled_seed_urls, upsert_asin

logger = get_logger("bots.asin_discovery")

# Amazon /dp/ ASIN pattern (10 alphanumeric) – used for file:// fixture and fallback
_ASIN_PATTERN = re.compile(r"/dp/([A-Z0-9]{10})", re.I)


def _is_amazon_listing_url(url: str) -> bool:
    """True if URL is a real Amazon listing/category/search page (not file:// or about:blank)."""
    if not url or url.startswith("file:") or url == "about:blank":
        return False
    return "amazon" in url.lower()


class AsinDiscoveryBot:
    """
    Discovers ASINs from category/listing pages. Uses central proxy and browser layer.
    run() opens a session, navigates to given URLs (or about:blank), extracts ASINs, saves, returns asin list.
    """

    def __init__(self) -> None:
        pass

    def _discover_from_page(self, page, url: str) -> List[Dict[str, Any]]:
        """
        Extract ASINs from current page from links matching /dp/ASIN.
        Returns list of dicts with at least "asin"; optional keys for metadata when available.
        """
        items: List[Dict[str, Any]] = []
        try:
            hrefs = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href*="/dp/"]')).map(a => a.href);
            }""")
        except Exception as e:
            logger.warning("_discover_from_page evaluate failed: %s", e)
            return []
        seen: set = set()
        for href in (hrefs or []):
            match = _ASIN_PATTERN.search(href)
            if match:
                asin = match.group(1).upper()
                if asin not in seen:
                    seen.add(asin)
                    items.append({"asin": asin})
        return items

    def _save_discovered(self, items: List[Dict[str, Any]]) -> List[int]:
        """Persist discovered ASINs; returns list of asins.id."""
        ids = []
        for item in items:
            asin = item.get("asin")
            if not asin:
                continue
            try:
                pid = upsert_asin(
                    asin,
                    title=item.get("title"),
                    brand=item.get("brand"),
                    category=item.get("category"),
                    product_url=item.get("product_url"),
                    main_image_url=item.get("main_image_url"),
                )
                ids.append(pid)
            except Exception as e:
                logger.warning("upsert_asin failed for %s: %s", asin, e)
        return ids

    def run(
        self,
        categories: Optional[List[str]] = None,
        urls: Optional[List[str]] = None,
        max_items: Optional[int] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Run discovery: open browser, visit urls (or about:blank if none), extract ASINs, save to DB.
        Returns list of discovered ASIN strings. If workspace_id in kwargs, quota enforced (Step 55).
        """
        workspace_id = kwargs.get("workspace_id")
        if workspace_id is not None:
            from amazon_research.db import check_quota_and_raise
            check_quota_and_raise(workspace_id, "discovery_run")
        categories = categories or []
        if urls is None:
            urls = get_enabled_seed_urls()
        urls = urls or []
        logger.info(
            "asin_discovery run started",
            extra={"categories": categories, "urls_count": len(urls), "max_items": max_items},
        )

        discovered: List[Dict[str, Any]] = []
        session = kwargs.get("session")
        own_session = session is None
        if own_session:
            session = BrowserSession(headless=True)
            session.start()
        try:
            page = session.get_page()
            if not page:
                logger.warning("asin_discovery: no page")
                return []
            discovery_pages_visited = 0
            if urls:
                from amazon_research.config import get_config
                cfg = get_config()
                max_pages = max(1, min(cfg.max_discovery_pages, cfg.max_discovery_pages_cap))
                urls_capped = urls[:max_pages]
                for i, u in enumerate(urls_capped):
                    if max_items and len(discovered) >= max_items:
                        break
                    try:
                        session.goto_with_retry(u, wait_until="domcontentloaded")
                        discovery_pages_visited += 1
                        if _is_amazon_listing_url(u):
                            time.sleep(cfg.discovery_page_wait_sec)
                            from amazon_research.detection import is_captcha_or_bot_check
                            if is_captcha_or_bot_check(page):
                                logger.warning("asin_discovery: captcha/bot-check detected, stopping")
                                break
                            from amazon_research.parsers.listing import extract_asins_from_amazon_listing
                            discovered.extend(extract_asins_from_amazon_listing(page))
                        else:
                            discovered.extend(self._discover_from_page(page, u))
                        if i < len(urls_capped) - 1:
                            session.delay_between_actions()
                    except Exception as e:
                        logger.warning("discover from URL failed, stopping", extra={"error": str(e)})
                        break
                try:
                    from amazon_research.monitoring import record_bandwidth
                    record_bandwidth("discovery", pages=discovery_pages_visited)
                except Exception:
                    pass
            else:
                session.goto_with_retry("about:blank", wait_until="domcontentloaded")
                discovered = self._discover_from_page(page, "about:blank")
        finally:
            if own_session and session:
                session.close()

        # Dedupe by ASIN before save
        seen_asin: set = set()
        unique: List[Dict[str, Any]] = []
        for d in discovered:
            a = d.get("asin")
            if a and a not in seen_asin:
                seen_asin.add(a)
                unique.append(d)
        discovered = unique
        if max_items and len(discovered) > max_items:
            discovered = discovered[:max_items]
        if discovered:
            self._save_discovered(discovered)
        asin_list = [d["asin"] for d in discovered if d.get("asin")]
        logger.info("asin_discovery run finished", extra={"discovered": len(asin_list)})
        if workspace_id is not None:
            try:
                from amazon_research.db import record_audit
                record_audit(workspace_id, "discovery_run", {"asins_count": len(asin_list)})
            except Exception:
                pass
        return asin_list
