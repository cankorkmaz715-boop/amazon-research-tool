"""
Step 187: Opportunity signal enrichment – compute and attach demand, competition, trend, price_stability, listing_density.
Stores signals in signal_results; compatible with opportunity memory, scoring engine, trend engine, scheduler loop.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_signal_enrichment")


def _parse_opportunity_ref(opportunity_ref: str) -> tuple:
    """Return (market, asin) from ref e.g. DE:B08XXX -> ('DE', 'B08XXX')."""
    ref = (opportunity_ref or "").strip()
    if ":" in ref:
        parts = ref.split(":", 1)
        return (parts[0].strip().upper(), (parts[1] or "").strip().upper())
    return ("DE", ref.upper())


def _compute_demand_estimate(rating: Optional[float], review_count: Optional[int]) -> float:
    """Align with scoring engine: demand proxy 0–100 from rating and review_count."""
    r = (rating or 0) / 5.0
    rc = min(1.0, (review_count or 0) / 4000.0)
    raw = r * 50.0 + rc * 50.0
    return round(min(100.0, max(0.0, raw)), 2)


def _compute_competition_level(seller_count: Optional[int]) -> float:
    """Align with scoring engine: competition proxy 0–100."""
    s = seller_count or 0
    raw = min(100.0, s * 5.0)
    return round(max(0.0, raw), 2)


def _compute_trend_signal_from_trend_result(trend_result: Optional[Dict[str, Any]]) -> Optional[float]:
    """Derive a single trend_signal 0–100 from trend_results signals or trend score."""
    if not trend_result or not isinstance(trend_result, dict):
        return None
    signals = trend_result.get("signals") or {}
    if isinstance(signals, str):
        try:
            import json
            signals = json.loads(signals)
        except Exception:
            signals = {}
    trend_score = signals.get("trend_score")
    if trend_score is not None:
        try:
            return round(min(100.0, max(0.0, float(trend_score))), 2)
        except (TypeError, ValueError):
            pass
    # Fallback: aggregate from review/rating/price/rank trends
    n = 0
    total = 0.0
    for key in ("review_count", "rating", "price", "rank"):
        v = signals.get(key)
        if isinstance(v, dict) and v.get("trend") == "rising":
            total += 25.0
            n += 1
        elif isinstance(v, dict) and v.get("trend") == "stable":
            total += 15.0
            n += 1
    if n > 0:
        return round(min(100.0, total), 2)
    return None


def _compute_price_stability(price_history: List[Dict[str, Any]], current_price: Optional[float]) -> float:
    """Price stability 0–100: low variance = high stability. No history => 100 (stable)."""
    if not price_history or len(price_history) < 2:
        return 100.0
    prices = [p.get("price") for p in price_history if p.get("price") is not None]
    if len(prices) < 2:
        return 100.0
    try:
        mean = sum(prices) / len(prices)
        var = sum((p - mean) ** 2 for p in prices) / len(prices)
        if mean == 0:
            return 100.0
        cv = (var ** 0.5) / mean
        stability = max(0.0, 100.0 - min(100.0, cv * 100))
        return round(stability, 2)
    except Exception:
        return 100.0


def _compute_listing_density(review_count: Optional[int], seller_count: Optional[int]) -> float:
    """Listing density proxy 0–100: review volume and seller count as density indicators."""
    rc = min(1.0, (review_count or 0) / 5000.0) * 50.0
    sc = min(1.0, (seller_count or 0) / 20.0) * 50.0
    raw = rc + sc
    return round(min(100.0, max(0.0, raw)), 2)


def compute_signals_for_opportunity(
    opportunity_ref: str,
    memory_record: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compute demand_estimate, competition_level, trend_signal, price_stability, listing_density for one opportunity.
    Uses opportunity_memory context (market, asin), product_metrics, scoring_results, trend_results, price_history.
    Returns dict with signal keys and optional explanation.
    """
    market, asin = _parse_opportunity_ref(opportunity_ref)
    out: Dict[str, Any] = {
        "demand_estimate": None,
        "competition_level": None,
        "trend_signal": None,
        "price_stability": None,
        "listing_density": None,
        "marketplace": market,
    }
    if not asin:
        return out

    asin_id = None
    try:
        from amazon_research.db import get_asin_id, get_product_metrics_by_asin_ids
        asin_id = get_asin_id(asin)
    except Exception as e:
        logger.debug("compute_signals get_asin_id: %s", e)

    metrics = None
    if asin_id:
        try:
            from amazon_research.db import get_product_metrics_by_asin_ids
            rows = get_product_metrics_by_asin_ids([asin_id])
            metrics = rows[0] if rows else None
        except Exception as e:
            logger.debug("compute_signals get_product_metrics: %s", e)

    if metrics:
        rating = metrics.get("rating")
        review_count = metrics.get("review_count")
        out["demand_estimate"] = _compute_demand_estimate(rating, review_count)
        seller_count = metrics.get("seller_count")
        if seller_count is None and asin_id:
            try:
                from amazon_research.db.connection import get_connection
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT seller_count FROM product_metrics WHERE asin_id = %s", (asin_id,))
                r = cur.fetchone()
                cur.close()
                seller_count = r[0] if r else None
            except Exception:
                pass
        out["competition_level"] = _compute_competition_level(seller_count)
        out["listing_density"] = _compute_listing_density(review_count, seller_count)

    try:
        from amazon_research.db.trend_persistence import get_trend_result_latest
        trend = get_trend_result_latest("asin", asin if asin_id is None else str(asin_id))
        out["trend_signal"] = _compute_trend_signal_from_trend_result(trend)
    except Exception as e:
        logger.debug("compute_signals trend: %s", e)

    price_history: List[Dict[str, Any]] = []
    if asin_id:
        try:
            from amazon_research.db.persistence import get_price_history
            price_history = get_price_history(asin_id, limit=30)
        except Exception:
            pass
    current_price = metrics.get("price") if metrics else None
    out["price_stability"] = _compute_price_stability(price_history, current_price)

    return out


def enrich_and_store_signals(
    opportunity_ref: str,
    memory_record: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """
    Compute signals for the opportunity and store in signal_results. Optionally attach to opportunity (context).
    Returns signal_results id or None.
    """
    signals = compute_signals_for_opportunity(opportunity_ref, memory_record=memory_record)
    try:
        from amazon_research.db.signal_results import insert_signal_result
        rid = insert_signal_result(
            opportunity_ref,
            demand_estimate=signals.get("demand_estimate"),
            competition_level=signals.get("competition_level"),
            trend_signal=signals.get("trend_signal"),
            price_stability=signals.get("price_stability"),
            listing_density=signals.get("listing_density"),
            marketplace=signals.get("marketplace"),
            signals=signals,
        )
        if rid and memory_record:
            try:
                from amazon_research.db.opportunity_memory import record_opportunity_seen
                ctx = dict(memory_record.get("context") or {})
                ctx["latest_signals"] = signals
                record_opportunity_seen(opportunity_ref, context=ctx, workspace_id=memory_record.get("workspace_id"))
            except Exception as e:
                logger.debug("enrich_and_store attach to memory: %s", e)
        return rid
    except Exception as e:
        logger.debug("enrich_and_store insert_signal_result: %s", e)
        return None


def enrich_opportunities_from_memory(
    limit: int = 50,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Load opportunities from opportunity_memory, compute and store signals for each.
    Compatible with scheduler loop. Returns summary: processed, stored, errors.
    """
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("enrich_opportunities_from_memory list: %s", e)
        return {"processed": 0, "stored": 0, "errors": 1}
    stored = 0
    for mem in rows or []:
        ref = (mem.get("opportunity_ref") or "").strip()
        if not ref:
            continue
        rid = enrich_and_store_signals(ref, memory_record=mem)
        if rid is not None:
            stored += 1
    return {"processed": len(rows or []), "stored": stored, "errors": 0}
