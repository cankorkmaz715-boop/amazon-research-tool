"""
PostgreSQL connection layer. Central place for DB access. Use init_db() once, then get_connection().
"""
from typing import Any, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("db")

_connection: Any = None


def get_connection():  # noqa: ANN201
    """Return the DB connection. Call init_db() first."""
    global _connection
    if _connection is None:
        raise RuntimeError("DB not initialized. Call init_db() first.")
    return _connection


def init_db(database_url: Optional[str] = None) -> None:
    """
    Connect to PostgreSQL and store the connection. Call once at startup.
    Uses DATABASE_URL from config if database_url not provided.
    """
    global _connection
    from amazon_research.config import get_config
    import psycopg2

    cfg = get_config()
    url = database_url or cfg.database_url
    if not url or not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("DATABASE_URL must be a PostgreSQL URL")

    _connection = psycopg2.connect(url)
    _connection.autocommit = False
    logger.info(
        "db connected",
        extra={"url_preview": url.split("@")[-1] if "@" in url else "***"},
    )
