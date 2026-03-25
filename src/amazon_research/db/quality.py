"""
Data quality checks (Step 26). DB-only: missing fields, invalid metrics, duplicate checks.
Compact summary for monitoring. No scraping/scheduler/parser changes.
"""
from typing import Any, Dict, List

from .connection import get_connection


def run_data_quality_checks() -> Dict[str, Any]:
    """
    Run quality checks on asins and product_metrics. Returns compact summary.
    Keys: missing_fields (list of descriptions), invalid_metrics (count), duplicate_issues (count), summary (str).
    """
    conn = get_connection()
    cur = conn.cursor()

    missing: List[str] = []
    invalid_count = 0
    duplicate_count = 0

    # 1) Missing or empty core fields (asins: title, product_url; metrics: all core null)
    cur.execute(
        """
        SELECT COUNT(*) FROM asins
        WHERE (title IS NULL OR TRIM(COALESCE(title, '')) = '')
           OR (product_url IS NULL OR TRIM(COALESCE(product_url, '')) = '')
        """
    )
    row = cur.fetchone()
    if row and row[0] and row[0] > 0:
        missing.append(f"asins missing title/url: {row[0]}")

    cur.execute(
        """
        SELECT COUNT(*) FROM product_metrics pm
        WHERE pm.price IS NULL AND pm.rating IS NULL AND pm.review_count IS NULL
        """
    )
    row = cur.fetchone()
    if row and row[0] and row[0] > 0:
        missing.append(f"metrics fully empty: {row[0]}")

    # 2) Suspicious invalid metric values
    cur.execute(
        """
        SELECT COUNT(*) FROM product_metrics
        WHERE (price IS NOT NULL AND price < 0)
           OR (rating IS NOT NULL AND (rating < 0 OR rating > 5))
           OR (review_count IS NOT NULL AND review_count < 0)
        """
    )
    row = cur.fetchone()
    if row and row[0]:
        invalid_count = row[0]

    # 3) Suspicious duplicates (schema enforces uniqueness; check for logical duplicates)
    cur.execute(
        "SELECT COUNT(*) FROM (SELECT asin_id, COUNT(*) c FROM product_metrics GROUP BY asin_id HAVING COUNT(*) > 1) x"
    )
    row = cur.fetchone()
    if row and row[0]:
        duplicate_count += row[0]

    cur.execute(
        "SELECT COUNT(*) FROM (SELECT asin, COUNT(*) c FROM asins GROUP BY asin HAVING COUNT(*) > 1) x"
    )
    row = cur.fetchone()
    if row and row[0]:
        duplicate_count += row[0]

    cur.close()

    # Compact summary
    parts = []
    if missing:
        parts.append("missing: " + "; ".join(missing))
    else:
        parts.append("missing: none")
    parts.append(f"invalid_metrics: {invalid_count}")
    parts.append(f"duplicate_issues: {duplicate_count}")
    summary = " | ".join(parts)

    return {
        "missing_fields": missing if missing else ["none"],
        "invalid_metrics": invalid_count,
        "duplicate_issues": duplicate_count,
        "summary": summary,
    }
