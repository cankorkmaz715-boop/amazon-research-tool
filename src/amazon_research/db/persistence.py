"""
Persistence layer: save/update ASINs, metrics, and history. Uses get_connection().
No scraping logic; called by discovery and refresh bots.
"""
from decimal import Decimal
from typing import List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.persistence")


def _dec(value):  # noqa: ANN001
    """Convert to Decimal for numeric columns; None stays None."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def upsert_asin(
    asin: str,
    title: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    product_url: Optional[str] = None,
    main_image_url: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> int:
    """
    Insert or update an ASIN. Returns asins.id. workspace_id optional (Step 41).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO asins (asin, title, brand, category, product_url, main_image_url, workspace_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (asin) DO UPDATE SET
            title = COALESCE(EXCLUDED.title, asins.title),
            brand = COALESCE(EXCLUDED.brand, asins.brand),
            category = COALESCE(EXCLUDED.category, asins.category),
            product_url = COALESCE(EXCLUDED.product_url, asins.product_url),
            main_image_url = COALESCE(EXCLUDED.main_image_url, asins.main_image_url),
            workspace_id = COALESCE(EXCLUDED.workspace_id, asins.workspace_id),
            updated_at = NOW()
        RETURNING id
        """,
        (asin, title, brand, category, product_url, main_image_url, workspace_id),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def upsert_product_metrics(
    asin_id: int,
    price: Optional[float] = None,
    currency: Optional[str] = None,
    bsr: Optional[str] = None,
    rating: Optional[float] = None,
    review_count: Optional[int] = None,
    seller_count: Optional[int] = None,
    fba_signal: Optional[str] = None,
) -> None:
    """Insert or update current product_metrics for one ASIN."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO product_metrics (asin_id, price, currency, bsr, rating, review_count, seller_count, fba_signal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (asin_id) DO UPDATE SET
            price = COALESCE(EXCLUDED.price, product_metrics.price),
            currency = COALESCE(EXCLUDED.currency, product_metrics.currency),
            bsr = COALESCE(EXCLUDED.bsr, product_metrics.bsr),
            rating = COALESCE(EXCLUDED.rating, product_metrics.rating),
            review_count = COALESCE(EXCLUDED.review_count, product_metrics.review_count),
            seller_count = COALESCE(EXCLUDED.seller_count, product_metrics.seller_count),
            fba_signal = COALESCE(EXCLUDED.fba_signal, product_metrics.fba_signal),
            updated_at = NOW()
        """,
        (asin_id, _dec(price), currency, bsr, _dec(rating), review_count, seller_count, fba_signal),
    )
    cur.close()
    conn.commit()


def get_product_metrics_by_asin_ids(asin_ids: List[int]) -> List[dict]:
    """
    Return current product_metrics for given asin_ids. Step 82: Opportunity ranking.
    Each row: asin_id, price, rating, review_count, bsr.
    """
    if not asin_ids:
        return []
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT asin_id, price, rating, review_count, bsr FROM product_metrics WHERE asin_id = ANY(%s)",
        (list(asin_ids),),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "asin_id": r[0],
            "price": float(r[1]) if r[1] is not None else None,
            "rating": float(r[2]) if r[2] is not None else None,
            "review_count": r[3],
            "bsr": r[4],
        }
        for r in rows
    ]


def append_price_history(asin_id: int, price: float, currency: Optional[str] = None) -> None:
    """Append one row to price_history."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO price_history (asin_id, price, currency) VALUES (%s, %s, %s)",
        (asin_id, _dec(price), currency),
    )
    cur.close()
    conn.commit()


def append_review_history(
    asin_id: int,
    review_count: Optional[int] = None,
    rating: Optional[float] = None,
) -> None:
    """Append one row to review_history."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO review_history (asin_id, review_count, rating) VALUES (%s, %s, %s)",
        (asin_id, review_count, _dec(rating)),
    )
    cur.close()
    conn.commit()


def get_price_history(asin_id: int, limit: int = 100) -> List[dict]:
    """
    Return price history for asin_id, oldest first. Step 80: Trend engine.
    Each row: price (float), recorded_at.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT price, recorded_at FROM price_history WHERE asin_id = %s ORDER BY recorded_at ASC LIMIT %s",
        (asin_id, max(1, limit)),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"price": float(r[0]) if r[0] is not None else None, "recorded_at": r[1]}
        for r in rows
    ]


def get_review_history(asin_id: int, limit: int = 100) -> List[dict]:
    """
    Return review/rating history for asin_id, oldest first. Step 80: Trend engine.
    Each row: review_count, rating, recorded_at.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT review_count, rating, recorded_at FROM review_history WHERE asin_id = %s ORDER BY recorded_at ASC LIMIT %s",
        (asin_id, max(1, limit)),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "review_count": r[0],
            "rating": float(r[1]) if r[1] is not None else None,
            "recorded_at": r[2],
        }
        for r in rows
    ]


def append_bsr_history(
    asin_id: int,
    marketplace: str,
    bsr: Optional[str] = None,
    category_context: Optional[str] = None,
) -> None:
    """
    Append one row to bsr_history. Step 101: BSR history engine.
    Lightweight, append-only. Used by refresh pipeline and consumed by trend engine.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bsr_history (asin_id, marketplace, bsr, category_context) VALUES (%s, %s, %s, %s)",
        (asin_id, (marketplace or "DE").strip() or "DE", bsr, category_context),
    )
    cur.close()
    conn.commit()


def get_bsr_history(asin_id: int, limit: int = 100) -> List[dict]:
    """
    Return BSR history for asin_id, oldest first. Step 101: trend engine, trend scoring, demand.
    Each row: recorded_at, marketplace, bsr, category_context.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT recorded_at, marketplace, bsr, category_context FROM bsr_history WHERE asin_id = %s ORDER BY recorded_at ASC LIMIT %s",
        (asin_id, max(1, limit)),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "recorded_at": r[0],
            "marketplace": r[1],
            "bsr": r[2],
            "category_context": r[3],
        }
        for r in rows
    ]


def get_asin_id(asin: str) -> Optional[int]:
    """Return asins.id for the given asin, or None if not found."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM asins WHERE asin = %s", (asin,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def get_asin_by_id(asin_id: int) -> Optional[str]:
    """Return asins.asin for the given id, or None if not found."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT asin FROM asins WHERE id = %s", (asin_id,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def get_asins_metadata(asin_list: List[str]) -> List[dict]:
    """
    Return id, asin, category, brand, title for each ASIN in asin_list (found in DB).
    Step 79/81: Niche detector and product clustering – metadata and title/token similarity.
    """
    if not asin_list:
        return []
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, asin, category, brand, title FROM asins WHERE asin = ANY(%s)",
        (list(asin_list),),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"id": r[0], "asin": r[1], "category": r[2], "brand": r[3], "title": r[4] if len(r) > 4 else None}
        for r in rows
    ]


def insert_scoring_result(
    asin_id: int,
    competition_score: Optional[float] = None,
    demand_score: Optional[float] = None,
    opportunity_score: Optional[float] = None,
) -> None:
    """Append one row to scoring_results."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO scoring_results (asin_id, competition_score, demand_score, opportunity_score)
        VALUES (%s, %s, %s, %s)
        """,
        (asin_id, _dec(competition_score), _dec(demand_score), _dec(opportunity_score)),
    )
    cur.close()
    conn.commit()


# --- Failure tracking (Step 22): asin_attempt_state ---

_MAX_ERROR_LEN = 500


def record_attempt(asin_id: int) -> None:
    """Set last_attempt_at = now() for this ASIN. Upsert row if missing."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO asin_attempt_state (asin_id, failure_count, last_attempt_at, updated_at)
        VALUES (%s, 0, NOW(), NOW())
        ON CONFLICT (asin_id) DO UPDATE SET last_attempt_at = NOW(), updated_at = NOW()
        """,
        (asin_id,),
    )
    cur.close()
    conn.commit()


def record_success(asin_id: int) -> None:
    """Set last_success_at, reset failure_count and skip_until."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO asin_attempt_state (asin_id, failure_count, last_success_at, skip_until, updated_at)
        VALUES (%s, 0, NOW(), NULL, NOW())
        ON CONFLICT (asin_id) DO UPDATE SET
            failure_count = 0,
            last_success_at = NOW(),
            skip_until = NULL,
            updated_at = NOW()
        """,
        (asin_id,),
    )
    cur.close()
    conn.commit()


def record_failure(asin_id: int, error_message: Optional[str] = None) -> None:
    """Increment failure_count, set last_error (truncated), last_attempt_at. Set skip_until if count >= threshold."""
    from amazon_research.config import get_config
    cfg = get_config()
    err = (error_message or "")[: _MAX_ERROR_LEN]
    thresh = cfg.skip_after_n_failures
    hours = cfg.skip_duration_hours
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO asin_attempt_state (asin_id, failure_count, last_error, last_attempt_at, skip_until, updated_at)
        VALUES (%s, 1, %s, NOW(), CASE WHEN 1 >= %s THEN NOW() + (INTERVAL '1 hour' * %s) ELSE NULL END, NOW())
        ON CONFLICT (asin_id) DO UPDATE SET
            failure_count = asin_attempt_state.failure_count + 1,
            last_error = EXCLUDED.last_error,
            last_attempt_at = NOW(),
            skip_until = CASE
                WHEN asin_attempt_state.failure_count + 1 >= %s THEN NOW() + (INTERVAL '1 hour' * %s)
                ELSE asin_attempt_state.skip_until
            END,
            updated_at = NOW()
        """,
        (asin_id, err, thresh, hours, thresh, hours),
    )
    cur.close()
    conn.commit()


def should_skip_asin(asin_id: int) -> bool:
    """True if ASIN is temporarily skippable (skip_until > now())."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM asin_attempt_state WHERE asin_id = %s AND skip_until IS NOT NULL AND skip_until > NOW()",
        (asin_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row is not None
