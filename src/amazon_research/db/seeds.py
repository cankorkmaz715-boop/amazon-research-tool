"""
Discovery seed management – add, list, enable/disable category/search URLs for discovery.
Step 37: DB-driven seed source; no fan-out expansion.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.seeds")


def add_seed(
    url: str,
    label: Optional[str] = None,
    enabled: bool = True,
) -> int:
    """Insert a discovery seed. Returns discovery_seeds.id. Reuses existing row if url exists (update enabled/label)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO discovery_seeds (url, label, enabled)
        VALUES (%s, %s, %s)
        ON CONFLICT (url) DO UPDATE SET
            label = COALESCE(EXCLUDED.label, discovery_seeds.label),
            enabled = EXCLUDED.enabled,
            updated_at = NOW()
        RETURNING id
        """,
        (url.strip(), (label or "").strip() or None, enabled),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def list_seeds(
    enabled_only: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Return list of seeds as dicts with id, url, label, enabled, created_at, updated_at."""
    conn = get_connection()
    cur = conn.cursor()
    if enabled_only is True:
        cur.execute(
            "SELECT id, url, label, enabled, created_at, updated_at FROM discovery_seeds WHERE enabled = true ORDER BY id"
        )
    elif enabled_only is False:
        cur.execute(
            "SELECT id, url, label, enabled, created_at, updated_at FROM discovery_seeds WHERE enabled = false ORDER BY id"
        )
    else:
        cur.execute(
            "SELECT id, url, label, enabled, created_at, updated_at FROM discovery_seeds ORDER BY id"
        )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "id": r[0],
            "url": r[1],
            "label": r[2],
            "enabled": r[3],
            "created_at": r[4],
            "updated_at": r[5],
        }
        for r in rows
    ]


def set_seed_enabled(seed_id: int, enabled: bool) -> bool:
    """Set enabled state for a seed by id. Returns True if a row was updated."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE discovery_seeds SET enabled = %s, updated_at = NOW() WHERE id = %s",
        (enabled, seed_id),
    )
    n = cur.rowcount
    cur.close()
    conn.commit()
    return n > 0


def get_enabled_seed_urls() -> List[str]:
    """Return ordered list of URL strings for enabled seeds only (for discovery bot)."""
    seeds = list_seeds(enabled_only=True)
    return [s["url"] for s in seeds]
