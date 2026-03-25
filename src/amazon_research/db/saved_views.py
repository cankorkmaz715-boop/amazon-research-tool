"""
Saved research views – workspace-scoped filter/sort presets. Step 42.
Lightweight, internal-first. Reuses API filter/sort concepts (category, asin, sort_by, order).
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.saved_views")


def create_saved_view(
    workspace_id: int,
    name: str,
    settings: Optional[Dict[str, Any]] = None,
) -> int:
    """Create a saved view for the workspace. settings = { filters: {}, sort_by, order }. Returns id."""
    conn = get_connection()
    cur = conn.cursor()
    name_val = (name or "Untitled view").strip()
    settings_val = json.dumps(settings if isinstance(settings, dict) else {})
    cur.execute(
        """
        INSERT INTO saved_research_views (workspace_id, name, settings)
        VALUES (%s, %s, %s::jsonb)
        RETURNING id
        """,
        (workspace_id, name_val, settings_val),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def get_saved_view(view_id: int, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Load a saved view by id. If workspace_id provided, returns None when view is not in that workspace (Step 52)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, workspace_id, name, settings, created_at, updated_at FROM saved_research_views WHERE id = %s",
        (view_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    if workspace_id is not None and row[1] != workspace_id:
        return None
    settings = row[3]
    if hasattr(settings, "copy"):
        settings = dict(settings)
    elif isinstance(settings, str):
        try:
            settings = json.loads(settings)
        except Exception:
            settings = {}
    return {
        "id": row[0],
        "workspace_id": row[1],
        "name": row[2],
        "settings": settings or {},
        "created_at": row[4],
        "updated_at": row[5],
    }


def list_saved_views(workspace_id: int) -> List[Dict[str, Any]]:
    """List saved views for the workspace, newest first. workspace_id required (Step 52)."""
    if workspace_id is None:
        raise ValueError("workspace_id required")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, workspace_id, name, settings, created_at, updated_at
        FROM saved_research_views WHERE workspace_id = %s ORDER BY updated_at DESC
        """,
        (workspace_id,),
    )
    rows = cur.fetchall()
    cur.close()
    out = []
    for row in rows:
        settings = row[3]
        if hasattr(settings, "copy"):
            settings = dict(settings)
        elif isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except Exception:
                settings = {}
        out.append({
            "id": row[0],
            "workspace_id": row[1],
            "name": row[2],
            "settings": settings or {},
            "created_at": row[4],
            "updated_at": row[5],
        })
    return out


def update_saved_view(
    view_id: int,
    name: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """Update name and/or settings. Returns True if a row was updated."""
    conn = get_connection()
    cur = conn.cursor()
    updates = []
    params: List[Any] = []
    if name is not None:
        updates.append("name = %s")
        params.append(name.strip())
    if settings is not None:
        updates.append("settings = %s::jsonb")
        params.append(json.dumps(settings))
    if not updates:
        cur.close()
        return False
    params.append(view_id)
    cur.execute(
        f"UPDATE saved_research_views SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s",
        params,
    )
    n = cur.rowcount
    cur.close()
    conn.commit()
    return n > 0
