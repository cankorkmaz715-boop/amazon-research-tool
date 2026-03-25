"""
User / Workspace model v1. Step 41 – internal-first, minimal. No auth or signup.
"""
import re
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.workspace")


def _slugify(name: str) -> str:
    """Derive a safe slug from name for uniqueness."""
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-") or "default"
    return s[:64]


def create_workspace(name: str, slug: Optional[str] = None) -> int:
    """Create a workspace. Returns workspaces.id. Slug derived from name if not provided."""
    conn = get_connection()
    cur = conn.cursor()
    slug_val = (slug or "").strip() or _slugify(name)
    cur.execute(
        """
        INSERT INTO workspaces (name, slug)
        VALUES (%s, %s)
        ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, updated_at = NOW()
        RETURNING id
        """,
        (name or "Workspace", slug_val),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def get_workspace(workspace_id: int) -> Optional[Dict[str, Any]]:
    """Return workspace dict (id, name, slug, created_at, updated_at) or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, slug, created_at, updated_at FROM workspaces WHERE id = %s",
        (workspace_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "slug": row[2],
        "created_at": row[3],
        "updated_at": row[4],
    }


def list_workspaces() -> List[Dict[str, Any]]:
    """Return all workspaces as list of dicts."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, slug, created_at, updated_at FROM workspaces ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    return [
        {"id": r[0], "name": r[1], "slug": r[2], "created_at": r[3], "updated_at": r[4]}
        for r in rows
    ]


def create_user(workspace_id: int, identifier: str) -> int:
    """Create a user linked to workspace. Returns users.id. identifier = email or username."""
    conn = get_connection()
    cur = conn.cursor()
    ident = (identifier or "").strip()
    if not ident:
        raise ValueError("identifier required")
    cur.execute(
        """
        INSERT INTO users (workspace_id, identifier)
        VALUES (%s, %s)
        ON CONFLICT (workspace_id, identifier) DO UPDATE SET updated_at = NOW()
        RETURNING id
        """,
        (workspace_id, ident),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def get_users_for_workspace(workspace_id: int) -> List[Dict[str, Any]]:
    """Return users in the workspace as list of dicts (id, workspace_id, identifier, created_at, updated_at)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, workspace_id, identifier, created_at, updated_at FROM users WHERE workspace_id = %s ORDER BY id",
        (workspace_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"id": r[0], "workspace_id": r[1], "identifier": r[2], "created_at": r[3], "updated_at": r[4]}
        for r in rows
    ]


def list_asins_by_workspace(workspace_id: Optional[int]) -> List[Dict[str, Any]]:
    """List asins scoped by workspace_id. Pass None for global (workspace_id IS NULL)."""
    conn = get_connection()
    cur = conn.cursor()
    if workspace_id is None:
        cur.execute(
            "SELECT id, asin, workspace_id, created_at FROM asins WHERE workspace_id IS NULL ORDER BY id"
        )
    else:
        cur.execute(
            "SELECT id, asin, workspace_id, created_at FROM asins WHERE workspace_id = %s ORDER BY id",
            (workspace_id,),
        )
    rows = cur.fetchall()
    cur.close()
    return [
        {"id": r[0], "asin": r[1], "workspace_id": r[2], "created_at": r[3]}
        for r in rows
    ]
