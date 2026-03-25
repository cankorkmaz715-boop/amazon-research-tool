"""
Data refresh bot – revisits known ASINs, updates metrics, stores history.
Refresh Batch v2: small batch (3–5 ASINs cap), sequential, delay between products, stop on repeated failures.
"""
import time
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.browser import BrowserSession
from amazon_research.db import (
    get_connection,
    get_asin_id,
    persist_related_sponsored_candidates,
    record_attempt,
    record_failure,
    record_success,
    should_skip_asin,
    upsert_product_metrics,
    append_bsr_history,
    append_price_history,
    append_review_history,
)

logger = get_logger("bots.data_refresh")


class DataRefreshBot:
    """
    Refreshes data for known ASINs. Loads ASINs from DB or accepts a list.
    For each ASIN: open product URL, wait, parse metrics from page, persist.
    """

    def __init__(self) -> None:
        pass

    def _refresh_one(self, page, asin: str) -> Dict[str, Any]:
        """
        Parse current page (must be product page for this ASIN). Returns metrics dict or {}.
        """
        from amazon_research.parsers.product import extract_metrics_from_product_page
        return extract_metrics_from_product_page(page)

    def _save_metrics(
        self,
        asin_id: int,
        metrics: Dict[str, Any],
        marketplace: Optional[str] = None,
    ) -> None:
        """Write to product_metrics and append to price_history / review_history / bsr_history when present."""
        if not metrics:
            return
        upsert_product_metrics(
            asin_id,
            price=metrics.get("price"),
            currency=metrics.get("currency"),
            bsr=metrics.get("bsr"),
            rating=metrics.get("rating"),
            review_count=metrics.get("review_count"),
            seller_count=metrics.get("seller_count"),
            fba_signal=metrics.get("fba_signal"),
        )
        if metrics.get("price") is not None:
            append_price_history(asin_id, float(metrics["price"]), metrics.get("currency"))
        if metrics.get("review_count") is not None or metrics.get("rating") is not None:
            append_review_history(
                asin_id,
                review_count=metrics.get("review_count"),
                rating=metrics.get("rating"),
            )
        if metrics.get("bsr") is not None:
            market = (marketplace or "").strip() or None
            if not market:
                try:
                    from amazon_research.market import get_default_market
                    market = get_default_market()
                except Exception:
                    market = "DE"
            append_bsr_history(
                asin_id,
                marketplace=market,
                bsr=metrics.get("bsr"),
                category_context=metrics.get("category"),
            )

    def _load_asin_list(self, limit: Optional[int]) -> List[str]:
        """Load ASIN strings from DB, optionally limited."""
        conn = get_connection()
        cur = conn.cursor()
        if limit:
            cur.execute("SELECT asin FROM asins ORDER BY id LIMIT %s", (limit,))
        else:
            cur.execute("SELECT asin FROM asins ORDER BY id")
        rows = cur.fetchall()
        cur.close()
        return [r[0] for r in rows]

    def run(
        self,
        asin_list: Optional[List[str]] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> int:
        """
        Run refresh for ASINs. If asin_list is None, load from DB (up to limit).
        If workspace_id in kwargs, quota enforced (Step 55).
        """
        workspace_id = kwargs.get("workspace_id")
        if workspace_id is not None:
            from amazon_research.db import check_quota_and_raise
            check_quota_and_raise(workspace_id, "refresh_run")
        if asin_list is None:
            asin_list = self._load_asin_list(limit)
        else:
            asin_list = asin_list[:limit] if limit else asin_list
        if not asin_list:
            logger.info("data_refresh run: no ASINs to refresh")
            return 0
        from amazon_research.config import get_config
        cfg = get_config()
        batch_cap = max(1, min(cfg.max_refresh_batch_size, cfg.max_refresh_batch_size_cap))
        max_failures = max(1, cfg.max_refresh_consecutive_failures)
        asin_list = asin_list[:batch_cap]
        try:
            from amazon_research.market import get_product_base_url
            product_base = get_product_base_url()
        except Exception:
            product_base = cfg.amazon_product_base_url
        wait_sec = cfg.refresh_page_wait_sec
        logger.info("data_refresh run started", extra={"asin_count": len(asin_list)})
        updated = 0
        consecutive_failures = 0
        session = kwargs.get("session")
        own_session = session is None
        if own_session:
            session = BrowserSession(headless=True)
            session.start()
        try:
            page = session.get_page()
            if not page:
                logger.warning("data_refresh: no page")
                return 0
            for i, asin in enumerate(asin_list):
                if consecutive_failures >= max_failures:
                    logger.warning("data_refresh: stopping after %s consecutive failures", max_failures)
                    break
                asin_id = get_asin_id(asin)
                if not asin_id:
                    logger.debug("data_refresh: asin not in DB, skip", extra={"asin": asin[:10] + "…" if len(asin) > 10 else asin})
                    continue
                if should_skip_asin(asin_id):
                    logger.debug("data_refresh: asin skipped (failure backoff)", extra={"asin_id": asin_id})
                    continue
                url = f"{product_base}{asin}"
                record_attempt(asin_id)
                try:
                    session.goto_with_retry(url, wait_until="domcontentloaded")
                    time.sleep(wait_sec)
                    try:
                        from amazon_research.monitoring import record_bandwidth
                        record_bandwidth("refresh", pages=1)
                    except Exception:
                        pass
                    from amazon_research.detection import is_captcha_or_bot_check
                    if is_captcha_or_bot_check(page):
                        logger.warning("data_refresh: captcha/bot-check detected, aborting for ASIN", extra={"asin_id": asin_id})
                        record_failure(asin_id, "captcha_detected")
                        consecutive_failures += 1
                        continue
                    metrics = self._refresh_one(page, asin)
                    if metrics:
                        marketplace = kwargs.get("marketplace")
                        self._save_metrics(asin_id, metrics, marketplace=marketplace)
                        record_success(asin_id)
                        updated += 1
                        consecutive_failures = 0
                        # Step 39: optional related/sponsored discovery from product page
                        if getattr(cfg, "discover_related_sponsored", False) and (
                            getattr(cfg, "max_related_per_page", 0) > 0 or getattr(cfg, "max_sponsored_per_page", 0) > 0
                        ):
                            try:
                                from amazon_research.parsers.related_sponsored import extract_related_sponsored_candidates
                                candidates = extract_related_sponsored_candidates(
                                    page,
                                    max_related=cfg.max_related_per_page,
                                    max_sponsored=cfg.max_sponsored_per_page,
                                )
                                if candidates:
                                    n = persist_related_sponsored_candidates(asin_id, candidates)
                                    if n:
                                        logger.info("data_refresh: related/sponsored edges stored", extra={"count": n})
                                        try:
                                            from amazon_research.monitoring import record_cost_hint
                                            record_cost_hint("related_sponsored", "candidates", n)
                                        except Exception:
                                            pass
                            except Exception as e:
                                logger.warning("data_refresh: related/sponsored extraction failed: %s", e)
                    else:
                        record_failure(asin_id, "no metrics extracted")
                        consecutive_failures += 1
                except Exception as e:
                    record_failure(asin_id, str(e))
                    logger.warning("data_refresh: page failed", extra={"error": str(e)})
                    consecutive_failures += 1
                if i < len(asin_list) - 1:
                    session.delay_between_actions()
        finally:
            if own_session and session:
                session.close()
        logger.info("data_refresh run finished", extra={"updated": updated})
        if workspace_id is not None:
            try:
                from amazon_research.db import record_audit
                record_audit(workspace_id, "refresh_run", {"updated": updated})
            except Exception:
                pass
        return updated
