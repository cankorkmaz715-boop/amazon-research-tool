"""
Opportunity scoring engine – competition, demand, opportunity scores. Persists to scoring_results.
Real Scoring v1: use stored product_metrics only (no scraping). Simple, transparent formulas.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.db import get_connection, get_asin_id, insert_scoring_result

logger = get_logger("bots.scoring_engine")

# Score scale 0–100. Formulas are intentional and documented for tuning.
def _compute_demand_score(rating: Optional[float], review_count: Optional[int]) -> float:
    """Demand proxy: rating (quality) + review volume. 0–100."""
    r = (rating or 0) / 5.0
    rc = min(1.0, (review_count or 0) / 4000.0)
    raw = r * 50.0 + rc * 50.0
    return round(min(100.0, max(0.0, raw)), 2)


def _compute_competition_score(seller_count: Optional[int]) -> float:
    """Competition proxy: more sellers = higher score. 0–100."""
    s = seller_count or 0
    raw = min(100.0, s * 5.0)
    return round(max(0.0, raw), 2)


def _compute_opportunity_score(demand: float, competition: float) -> float:
    """Opportunity = demand minus half of competition. 0–100."""
    raw = demand - 0.5 * competition
    return round(min(100.0, max(0.0, raw)), 2)


class ScoringEngine:
    """
    Computes and persists opportunity/competition/demand scores per ASIN.
    run() loads ASINs (from list or DB), calls _score_one() per ASIN, writes to scoring_results.
    """

    def __init__(self) -> None:
        pass

    def _load_metrics(self, asin_id: int) -> Optional[Dict[str, Any]]:
        """Load current product_metrics for asin_id. Returns dict or None."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT price, currency, bsr, rating, review_count, seller_count, fba_signal FROM product_metrics WHERE asin_id = %s",
            (asin_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return {
            "price": float(row[0]) if row[0] is not None else None,
            "currency": row[1],
            "bsr": row[2],
            "rating": float(row[3]) if row[3] is not None else None,
            "review_count": row[4],
            "seller_count": row[5],
            "fba_signal": row[6],
        }

    def _score_one(self, asin_id: int, metrics: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute competition_score, demand_score, opportunity_score from stored metrics only.
        Uses _compute_demand_score, _compute_competition_score, _compute_opportunity_score.
        """
        if not metrics:
            return {
                "competition_score": 0.0,
                "demand_score": 0.0,
                "opportunity_score": 0.0,
            }
        demand = _compute_demand_score(metrics.get("rating"), metrics.get("review_count"))
        competition = _compute_competition_score(metrics.get("seller_count"))
        opportunity = _compute_opportunity_score(demand, competition)
        return {
            "competition_score": competition,
            "demand_score": demand,
            "opportunity_score": opportunity,
        }

    def _load_asin_list(self, limit: Optional[int]) -> List[str]:
        """Load ASIN strings from DB."""
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
    ) -> List[Dict[str, Any]]:
        """
        Score ASINs. If asin_list is None, load from DB (up to limit).
        Returns list of dicts: asin, competition_score, demand_score, opportunity_score.
        """
        if asin_list is None:
            asin_list = self._load_asin_list(limit)
        else:
            asin_list = asin_list[:limit] if limit else asin_list
        if not asin_list:
            logger.info("scoring_engine run: no ASINs")
            return []
        logger.info("scoring_engine run started", extra={"asin_count": len(asin_list)})
        results = []
        for asin in asin_list:
            asin_id = get_asin_id(asin)
            if not asin_id:
                continue
            metrics = self._load_metrics(asin_id)
            scores = self._score_one(asin_id, metrics)
            insert_scoring_result(
                asin_id,
                competition_score=scores.get("competition_score"),
                demand_score=scores.get("demand_score"),
                opportunity_score=scores.get("opportunity_score"),
            )
            results.append({"asin": asin, **scores})
        logger.info("scoring_engine run finished", extra={"scored": len(results)})
        return results
