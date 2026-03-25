"""
Competition estimator foundation. Step 85 – evaluate clusters/niche candidates with competition signals.
Rule-based: review concentration, rating strength, cluster density, brand repetition, price homogeneity.
Extensible for demand vs competition modeling.
"""
import math
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("competition.estimator")


def _gather_competition_signals(
    cluster: Dict[str, Any],
    asin_to_id: Dict[str, int],
    metrics_by_id: Dict[int, Dict[str, Any]],
    metadata_by_asin: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build competition-related signals for one cluster."""
    member_asins = cluster.get("member_asins") or []
    cluster_size = len(member_asins)
    asin_ids = [asin_to_id[a] for a in member_asins if asin_to_id.get(a)]

    review_counts = []
    ratings = []
    prices = []
    brands = []

    for aid in asin_ids:
        m = metrics_by_id.get(aid) or {}
        if m.get("review_count") is not None:
            review_counts.append(int(m["review_count"]))
        if m.get("rating") is not None:
            ratings.append(float(m["rating"]))
        if m.get("price") is not None:
            prices.append(float(m["price"]))
    for a in member_asins:
        meta = metadata_by_asin.get(a) or {}
        b = (meta.get("brand") or "").strip()
        if b:
            brands.append(b)

    avg_review = sum(review_counts) / len(review_counts) if review_counts else None
    avg_rating = sum(ratings) / len(ratings) if ratings else None
    avg_price = sum(prices) / len(prices) if prices else None

    review_concentration = None
    if len(review_counts) > 1 and avg_review and avg_review > 0:
        variance = sum((x - avg_review) ** 2 for x in review_counts) / len(review_counts)
        std = math.sqrt(variance)
        review_concentration = std / avg_review if avg_review else None  # coefficient of variation

    rating_strength = avg_rating

    cluster_density = cluster_size  # saturation: more members = more dense

    unique_brands = len(set(brands))
    brand_concentration = None
    if brands and unique_brands > 0:
        brand_concentration = 1.0 - (unique_brands / len(brands))  # high if few brands dominate

    price_std = None
    price_homogeneity = None
    if len(prices) > 1 and avg_price and avg_price > 0:
        variance = sum((x - avg_price) ** 2 for x in prices) / len(prices)
        price_std = math.sqrt(variance)
        price_homogeneity = 1.0 - min(1.0, price_std / avg_price)  # high = compressed prices

    return {
        "cluster_size": cluster_size,
        "avg_review_count": avg_review,
        "review_concentration": review_concentration,
        "rating_strength": avg_rating,
        "cluster_density": cluster_density,
        "unique_brands": unique_brands,
        "brand_concentration": brand_concentration,
        "avg_price": avg_price,
        "price_std": price_std,
        "price_homogeneity": price_homogeneity,
    }


def _compute_competition_score(signals: Dict[str, Any]) -> tuple:
    """
    Rule-based competition score 0–100 (higher = more competitive). Returns (score, level, explanation).
    """
    score = 0.0
    parts = []

    cluster_size = signals.get("cluster_size") or 0
    density_norm = min(1.0, cluster_size / 15.0) * 20.0  # up to 20 pts
    score += density_norm
    parts.append(f"density={cluster_size}")

    avg_review = signals.get("avg_review_count")
    if avg_review is not None:
        rev_norm = min(1.0, math.log1p(avg_review) / 6.0) * 25.0  # review concentration proxy
        score += rev_norm
        parts.append(f"reviews~{avg_review:.0f}")

    avg_rating = signals.get("rating_strength")
    if avg_rating is not None:
        r_norm = max(0, min(1.0, (avg_rating - 3.0) / 2.0)) * 20.0  # 3–5 → 0–20
        score += r_norm
        parts.append(f"rating={avg_rating:.1f}")

    brand_conc = signals.get("brand_concentration")
    if brand_conc is not None:
        score += brand_conc * 15.0
        parts.append(f"brand_conc={brand_conc:.2f}")

    price_hom = signals.get("price_homogeneity")
    if price_hom is not None:
        score += price_hom * 20.0
        parts.append(f"price_hom={price_hom:.2f}")

    score = max(0.0, min(100.0, score))

    if score < 33:
        level = "low"
    elif score < 66:
        level = "medium"
    else:
        level = "high"

    explanation = "; ".join(parts) if parts else "no signals"
    return score, level, explanation


def estimate_competition(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
) -> Dict[str, Any]:
    """
    Estimate competition for each cluster. Uses review concentration, rating strength, density,
    brand concentration, price homogeneity. Returns { estimates, summary } with competition_score,
    competition_level, explanation, competition_signals per cluster.
    """
    if not clusters:
        return {"estimates": [], "summary": {"total": 0}}

    all_asins = set()
    for c in clusters:
        all_asins.update(c.get("member_asins") or [])
    if asin_pool:
        all_asins &= set(asin_pool)
    all_asins = list(all_asins)

    asin_to_id: Dict[str, int] = {}
    metrics_by_id: Dict[int, Dict[str, Any]] = {}
    metadata_by_asin: Dict[str, Dict[str, Any]] = {}

    if use_db and all_asins:
        try:
            from amazon_research.db import get_asin_id, get_asins_metadata, get_product_metrics_by_asin_ids
            for a in all_asins:
                aid = get_asin_id(a)
                if aid:
                    asin_to_id[a] = aid
            asin_ids = list(asin_to_id.values())
            if asin_ids:
                metrics_list = get_product_metrics_by_asin_ids(asin_ids)
                metrics_by_id = {m["asin_id"]: m for m in metrics_list}
            meta_list = get_asins_metadata(all_asins)
            metadata_by_asin = {r["asin"]: r for r in meta_list}
        except Exception as e:
            logger.debug("estimate_competition: %s", e)

    estimates: List[Dict[str, Any]] = []
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id") or ""
        signals = _gather_competition_signals(
            cluster,
            asin_to_id,
            metrics_by_id,
            metadata_by_asin,
        )
        score, level, explanation = _compute_competition_score(signals)
        estimates.append({
            "cluster_id": cluster_id,
            "competition_score": round(score, 1),
            "competition_level": level,
            "explanation": explanation,
            "competition_signals": signals,
        })

    return {
        "estimates": estimates,
        "summary": {"total": len(estimates)},
    }
