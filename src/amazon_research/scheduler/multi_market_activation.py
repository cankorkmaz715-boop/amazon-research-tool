"""
Step 184: Multi-market crawler activation – safe activation across DE, US, AU.
Market-aware domain/URL building, category/keyword seed selection, discovery context persistence.
Explicit market separation; structured outputs (market, target_type, target_id, activation_status, timestamp).
Integrates with multi-marketplace engine, intelligent crawl scheduler, runtime, production loop, discovery storage.
Conservative, safe for 24/7; no aggressive high-volume. Extensible for per-market scheduling policies.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("scheduler.multi_market_activation")

# Target types for activation output
TARGET_TYPE_CATEGORY = "category"
TARGET_TYPE_KEYWORD = "keyword"
ACTIVATION_STATUS_ACTIVATED = "activated"
ACTIVATION_STATUS_SKIPPED = "skipped"
ACTIVATION_STATUS_NO_SEEDS = "no_seeds"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_production_markets() -> List[str]:
    """Return list of production markets for multi-market activation (DE, US, AU)."""
    try:
        from amazon_research.market import PRODUCTION_MARKETS
        return list(PRODUCTION_MARKETS)
    except Exception:
        return ["DE", "US", "AU"]


def build_category_url_for_market(category_url: str, market: str) -> str:
    """
    Ensure category URL is valid for the given market (domain routing).
    If category_url is full URL, derive domain from market and replace host if needed.
    If path-only, prepend https://{domain}.
    """
    from amazon_research.market.config import get_market_config
    url = (category_url or "").strip()
    market = (market or "DE").strip().upper()
    cfg = get_market_config(market)
    domain = (cfg or {}).get("domain", "www.amazon.de")
    if not url:
        return f"https://{domain}/s"
    if url.startswith("http://") or url.startswith("https://"):
        # Replace host with correct domain for market
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            path = parsed.path or "/s"
            query = f"?{parsed.query}" if parsed.query else ""
            return f"https://{domain}{path}{query}"
        except Exception:
            return f"https://{domain}/s"
    return f"https://{domain}{url}" if url.startswith("/") else f"https://{domain}/s?k={url}"


def get_search_url_for_market(keyword: str, market: str) -> str:
    """Return marketplace-specific search URL for keyword (domain routing)."""
    try:
        from amazon_research.market import get_search_url
        return get_search_url(keyword, market)
    except Exception:
        from amazon_research.market import get_domain
        from urllib.parse import quote_plus
        domain = get_domain(market)
        q = quote_plus((keyword or "").strip())
        return f"https://{domain}/s?k={q}" if q else f"https://{domain}/s"


def get_activation_targets_for_market(
    market: str,
    workspace_id: Optional[int] = None,
    limit_category: int = 5,
    limit_keyword: int = 5,
) -> List[Dict[str, Any]]:
    """
    Return activation targets for a single market. Explicit market separation; no cross-market mixing.
    Each item: market, target_type, target_id, seed_id, activation_status, timestamp.
    """
    results: List[Dict[str, Any]] = []
    ts = _now_iso()
    market = (market or "DE").strip().upper()

    try:
        from amazon_research.db.category_seeds import get_ready_category_seeds
        from amazon_research.db.keyword_seeds import get_ready_keyword_seeds
    except Exception as e:
        logger.debug("multi_market_activation seeds import: %s", e)
        return results

    # Category seeds for this market only
    try:
        cats = get_ready_category_seeds(
            workspace_id=workspace_id,
            marketplace=market,
            limit=max(1, limit_category),
            order_by_last_scanned=True,
        )
        for s in cats:
            url = (s.get("category_url") or "").strip()
            target_url = build_category_url_for_market(url, market)
            results.append({
                "market": market,
                "target_type": TARGET_TYPE_CATEGORY,
                "target_id": target_url,
                "seed_id": s.get("id"),
                "activation_status": ACTIVATION_STATUS_ACTIVATED,
                "timestamp": ts,
            })
    except Exception as e:
        logger.debug("multi_market_activation category seeds %s: %s", market, e)

    # Keyword seeds for this market only
    try:
        kws = get_ready_keyword_seeds(
            workspace_id=workspace_id,
            marketplace=market,
            limit=max(1, limit_keyword),
            order_by_last_scanned=True,
        )
        for s in kws:
            keyword = (s.get("keyword") or "").strip()
            search_url = get_search_url_for_market(keyword, market)
            results.append({
                "market": market,
                "target_type": TARGET_TYPE_KEYWORD,
                "target_id": keyword,
                "seed_id": s.get("id"),
                "activation_status": ACTIVATION_STATUS_ACTIVATED,
                "timestamp": ts,
            })
    except Exception as e:
        logger.debug("multi_market_activation keyword seeds %s: %s", market, e)

    return results


def get_multi_market_activation(
    markets: Optional[List[str]] = None,
    workspace_id: Optional[int] = None,
    limit_per_type: int = 5,
) -> List[Dict[str, Any]]:
    """
    Return activation targets across DE, US, AU (or given markets). One market per item; no context contamination.
    Structured output: market, target_type, target_id, seed_id, activation_status, timestamp.
    """
    markets = markets or get_production_markets()
    out: List[Dict[str, Any]] = []
    for m in markets:
        m = (m or "").strip().upper()
        if not m:
            continue
        items = get_activation_targets_for_market(
            market=m,
            workspace_id=workspace_id,
            limit_category=limit_per_type,
            limit_keyword=limit_per_type,
        )
        out.extend(items)
    return out


def to_scheduler_tasks_multi_market(
    activation_targets: List[Dict[str, Any]],
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Convert multi-market activation targets to scheduler tasks (payload includes marketplace).
    Compatible with worker queue and discovery storage (marketplace in payload).
    """
    tasks: List[Dict[str, Any]] = []
    for a in activation_targets:
        market = (a.get("market") or "DE").strip()
        target_type = a.get("target_type") or ""
        target_id = (a.get("target_id") or "").strip()
        if not target_id:
            continue
        if target_type == TARGET_TYPE_KEYWORD:
            tasks.append({
                "task_type": "keyword_scan",
                "target_source": target_id,
                "payload": {"keyword": target_id, "marketplace": market, "workspace_id": workspace_id},
            })
        elif target_type == TARGET_TYPE_CATEGORY:
            tasks.append({
                "task_type": "category_scan",
                "target_source": target_id,
                "payload": {"category_url": target_id, "marketplace": market, "workspace_id": workspace_id},
            })
    return tasks


def enqueue_multi_market_activation(
    markets: Optional[List[str]] = None,
    workspace_id: Optional[int] = None,
    limit_per_type: int = 5,
    scheduled_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Get multi-market activation targets, convert to tasks, enqueue jobs. Safe for 24/7; conservative volume.
    Returns job_ids, summary, activation_targets (for logging).
    """
    targets = get_multi_market_activation(markets=markets, workspace_id=workspace_id, limit_per_type=limit_per_type)
    tasks = to_scheduler_tasks_multi_market(targets, workspace_id=workspace_id)
    job_ids: List[int] = []
    by_market: Dict[str, int] = {}
    try:
        from amazon_research.db import enqueue_job
        for t in tasks:
            payload = t.get("payload") or {}
            market = (payload.get("marketplace") or "DE").strip()
            jid = enqueue_job(job_type=t.get("task_type") or "keyword_scan", workspace_id=workspace_id, payload=payload, scheduled_at=scheduled_at)
            if jid:
                job_ids.append(jid)
                by_market[market] = by_market.get(market, 0) + 1
    except Exception as e:
        logger.warning("enqueue_multi_market_activation: %s", e)
    return {
        "job_ids": job_ids,
        "summary": {"enqueued": len(job_ids), "by_market": by_market},
        "activation_targets": targets,
    }
