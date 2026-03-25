"""
Opportunity watchlists – workspace-scoped lists of ASINs/research candidates. Step 43.
Lightweight, internal-first. No notification logic in this step.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection
from .persistence import get_asin_by_id

logger = get_logger("db.watchlists")


def create_watchlist(workspace_id: int, name: str) -> int:
    """Create a watchlist for the workspace. Returns watchlists.id."""
    conn = get_connection()
    cur = conn.cursor()
    name_val = (name or "Watchlist").strip()
    cur.execute(
        "INSERT INTO watchlists (workspace_id, name) VALUES (%s, %s) RETURNING id",
        (workspace_id, name_val),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def get_watchlist(watchlist_id: int, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Load a watchlist by id. If workspace_id provided, returns None when watchlist is not in that workspace (Step 52)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, workspace_id, name, created_at, updated_at FROM watchlists WHERE id = %s",
        (watchlist_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    if workspace_id is not None and row[1] != workspace_id:
        return None
    return {
        "id": row[0],
        "workspace_id": row[1],
        "name": row[2],
        "created_at": row[3],
        "updated_at": row[4],
    }


def list_watchlists(workspace_id: int) -> List[Dict[str, Any]]:
    """List watchlists for the workspace, newest first. workspace_id required (Step 52)."""
    if workspace_id is None:
        raise ValueError("workspace_id required")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, workspace_id, name, created_at, updated_at FROM watchlists WHERE workspace_id = %s ORDER BY updated_at DESC",
        (workspace_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"id": r[0], "workspace_id": r[1], "name": r[2], "created_at": r[3], "updated_at": r[4]}
        for r in rows
    ]


def add_watchlist_item(watchlist_id: int, asin_id: int) -> bool:
    """Add an ASIN to the watchlist. Returns True if added, False if duplicate."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO watchlist_items (watchlist_id, asin_id)
            VALUES (%s, %s)
            ON CONFLICT (watchlist_id, asin_id) DO NOTHING
            RETURNING id
            """,
            (watchlist_id, asin_id),
        )
        row = cur.fetchone()
        added = row is not None
    finally:
        cur.close()
    conn.commit()
    if added:
        cur = conn.cursor()
        cur.execute("UPDATE watchlists SET updated_at = NOW() WHERE id = %s", (watchlist_id,))
        cur.close()
        conn.commit()
    return added


def remove_watchlist_item(watchlist_id: int, asin_id: int) -> bool:
    """Remove an ASIN from the watchlist. Returns True if a row was deleted."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM watchlist_items WHERE watchlist_id = %s AND asin_id = %s", (watchlist_id, asin_id))
    n = cur.rowcount
    cur.close()
    conn.commit()
    if n > 0:
        cur = conn.cursor()
        cur.execute("UPDATE watchlists SET updated_at = NOW() WHERE id = %s", (watchlist_id,))
        cur.close()
        conn.commit()
    return n > 0


def list_watchlist_items(watchlist_id: int, include_asin: bool = True) -> List[Dict[str, Any]]:
    """List items in the watchlist. Returns list of dicts with id, watchlist_id, asin_id, created_at; optionally asin string."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, watchlist_id, asin_id, created_at FROM watchlist_items WHERE watchlist_id = %s ORDER BY created_at",
        (watchlist_id,),
    )
    rows = cur.fetchall()
    cur.close()
    out = []
    for r in rows:
        item = {"id": r[0], "watchlist_id": r[1], "asin_id": r[2], "created_at": r[3]}
        if include_asin:
            item["asin"] = get_asin_by_id(r[2])
        out.append(item)
    return out
