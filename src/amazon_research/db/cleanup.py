"""
Retention and cleanup for logs/history (Step 35). Never deletes asins, product_metrics, scoring_results.
Conservative: only error_logs, bot_runs, price_history, review_history by config retention days.
"""
from typing import Dict, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.cleanup")


def cleanup_error_logs(older_than_days: Optional[int] = None) -> int:
    """Delete error_logs rows older than N days. Returns deleted count."""
    from amazon_research.config import get_config
    days = older_than_days if older_than_days is not None else get_config().error_logs_retention_days
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM error_logs WHERE created_at < NOW() - (%s || ' days')::INTERVAL", (str(days),))
    n = cur.rowcount
    cur.close()
    conn.commit()
    if n:
        logger.info("cleanup_error_logs deleted %s rows", n)
    return n


def cleanup_bot_runs(older_than_days: Optional[int] = None) -> int:
    """Delete bot_runs rows older than N days. Returns deleted count."""
    from amazon_research.config import get_config
    days = older_than_days if older_than_days is not None else get_config().bot_runs_retention_days
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM bot_runs WHERE started_at < NOW() - (%s || ' days')::INTERVAL", (str(days),))
    n = cur.rowcount
    cur.close()
    conn.commit()
    if n:
        logger.info("cleanup_bot_runs deleted %s rows", n)
    return n


def cleanup_price_history(older_than_days: Optional[int] = None) -> int:
    """Delete price_history rows older than N days. Returns deleted count."""
    from amazon_research.config import get_config
    days = older_than_days if older_than_days is not None else get_config().price_history_retention_days
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM price_history WHERE recorded_at < NOW() - (%s || ' days')::INTERVAL", (str(days),))
    n = cur.rowcount
    cur.close()
    conn.commit()
    if n:
        logger.info("cleanup_price_history deleted %s rows", n)
    return n


def cleanup_review_history(older_than_days: Optional[int] = None) -> int:
    """Delete review_history rows older than N days. Returns deleted count."""
    from amazon_research.config import get_config
    days = older_than_days if older_than_days is not None else get_config().review_history_retention_days
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM review_history WHERE recorded_at < NOW() - (%s || ' days')::INTERVAL", (str(days),))
    n = cur.rowcount
    cur.close()
    conn.commit()
    if n:
        logger.info("cleanup_review_history deleted %s rows", n)
    return n


def run_retention_cleanup() -> Dict[str, int]:
    """Run all retention cleanups; returns dict of table -> deleted count."""
    return {
        "error_logs": cleanup_error_logs(),
        "bot_runs": cleanup_bot_runs(),
        "price_history": cleanup_price_history(),
        "review_history": cleanup_review_history(),
    }
