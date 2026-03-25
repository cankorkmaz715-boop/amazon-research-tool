"""
Category seed manager v1. Step 73 – add, list, enable/disable, update scan metadata.
Workspace-aware; compatible with category crawler/scanner flow.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.category_seeds")


def add_category_seed(
    category_url: str,
    marketplace: str = "DE",
    label: Optional[str] = None,
    active: bool = True,
    workspace_id: Optional[int] = None,
) -> int:
    """Insert or update a category seed. Returns category_seeds.id. ON CONFLICT updates label, active, marketplace."""
    conn = get_connection()
    cur = conn.cursor()
    url = category_url.strip()
    market = (marketplace or "DE").strip() or "DE"
    cur.execute(
        """
        INSERT INTO category_seeds (workspace_id, marketplace, category_url, label, active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (category_url) DO UPDATE SET
            label = COALESCE(EXCLUDED.label, category_seeds.label),
            active = EXCLUDED.active,
            marketplace = EXCLUDED.marketplace,
            workspace_id = COALESCE(EXCLUDED.workspace_id, category_seeds.workspace_id),
            updated_at = NOW()
        RETURNING id
        """,
        (workspace_id, market, url, (label or "").strip() or None, active),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def list_category_seeds(
    workspace_id: Optional[int] = None,
    active_only: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Return seeds as dicts: id, workspace_id, marketplace, category_url, label, active, last_scanned_at, scan_metadata, created_at, updated_at."""
    conn = get_connection()
    cur = conn.cursor()
    conditions = []
    params: List[Any] = []
    if workspace_id is not None:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    if active_only is True:
        conditions.append("active = true")
    elif active_only is False:
        conditions.append("active = false")
    where = " AND ".join(conditions) if conditions else "1=1"
    cur.execute(
        f"""
        SELECT id, workspace_id, marketplace, category_url, label, active,
               last_scanned_at, scan_metadata, created_at, updated_at
        FROM category_seeds
        WHERE {where}
        ORDER BY id
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    out = []
    for r in rows:
        meta = r[7]
        if isinstance(meta, str) and meta:
            try:
                meta = json.loads(meta)
            except Exception:
                pass
        out.append({
            "id": r[0],
            "workspace_id": r[1],
            "marketplace": r[2],
            "category_url": r[3],
            "label": r[4],
            "active": r[5],
            "last_scanned_at": r[6],
            "scan_metadata": meta,
            "created_at": r[8],
            "updated_at": r[9],
        })
    return out


def get_category_seed(seed_id: int) -> Optional[Dict[str, Any]]:
    """Return one category seed by id or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, workspace_id, marketplace, category_url, label, active,
               last_scanned_at, scan_metadata, created_at, updated_at
        FROM category_seeds WHERE id = %s
        """,
        (seed_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    meta = row[7]
    if isinstance(meta, str) and meta:
        try:
            meta = json.loads(meta)
        except Exception:
            pass
    return {
        "id": row[0],
        "workspace_id": row[1],
        "marketplace": row[2],
        "category_url": row[3],
        "label": row[4],
        "active": row[5],
        "last_scanned_at": row[6],
        "scan_metadata": meta,
        "created_at": row[8],
        "updated_at": row[9],
    }


def set_category_seed_active(seed_id: int, active: bool) -> bool:
    """Set active state for a seed. Returns True if a row was updated."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE category_seeds SET active = %s, updated_at = NOW() WHERE id = %s",
        (active, seed_id),
    )
    n = cur.rowcount
    cur.close()
    conn.commit()
    return n > 0


def update_category_seed_scan(
    seed_id: int,
    last_scanned_at: Optional[Any] = None,
    scan_metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Update last_scanned_at and/or scan_metadata for a seed. Returns True if a row was updated."""
    conn = get_connection()
    cur = conn.cursor()
    if last_scanned_at is not None and scan_metadata is not None:
        meta_json = json.dumps(scan_metadata) if scan_metadata else None
        cur.execute(
            """
            UPDATE category_seeds
            SET last_scanned_at = %s, scan_metadata = %s::jsonb, updated_at = NOW()
            WHERE id = %s
            """,
            (last_scanned_at, meta_json, seed_id),
        )
    elif last_scanned_at is not None:
        cur.execute(
            "UPDATE category_seeds SET last_scanned_at = %s, updated_at = NOW() WHERE id = %s",
            (last_scanned_at, seed_id),
        )
    elif scan_metadata is not None:
        meta_json = json.dumps(scan_metadata)
        cur.execute(
            "UPDATE category_seeds SET scan_metadata = %s::jsonb, updated_at = NOW() WHERE id = %s",
            (meta_json, seed_id),
        )
    else:
        cur.close()
        return False
    n = cur.rowcount
    cur.close()
    conn.commit()
    return n > 0


def get_active_category_seed_urls(workspace_id: Optional[int] = None) -> List[str]:
    """Return category_url list for active seeds only (for category scanner)."""
    seeds = list_category_seeds(workspace_id=workspace_id, active_only=True)
    return [s["category_url"] for s in seeds]


def get_ready_category_seeds(
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    limit: int = 10,
    order_by_last_scanned: bool = True,
) -> List[Dict[str, Any]]:
    """
    Step 74: Return active seeds ready for scanning. Optional filter by workspace_id and marketplace.
    When order_by_last_scanned is True, order by last_scanned_at ASC NULLS FIRST (least recently scanned first).
    """
    conn = get_connection()
    cur = conn.cursor()
    conditions = ["active = true"]
    params: List[Any] = []
    if workspace_id is not None:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    if marketplace:
        conditions.append("marketplace = %s")
        params.append(marketplace.strip())
    where = " AND ".join(conditions)
    order = "ORDER BY last_scanned_at ASC NULLS FIRST, id ASC" if order_by_last_scanned else "ORDER BY id ASC"
    params.append(max(1, limit))
    cur.execute(
        f"""
        SELECT id, workspace_id, marketplace, category_url, label, active,
               last_scanned_at, scan_metadata, created_at, updated_at
        FROM category_seeds
        WHERE {where}
        {order}
        LIMIT %s
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    out = []
    for r in rows:
        meta = r[7]
        if isinstance(meta, str) and meta:
            try:
                meta = json.loads(meta)
            except Exception:
                pass
        out.append({
            "id": r[0],
            "workspace_id": r[1],
            "marketplace": r[2],
            "category_url": r[3],
            "label": r[4],
            "active": r[5],
            "last_scanned_at": r[6],
            "scan_metadata": meta,
            "created_at": r[8],
            "updated_at": r[9],
        })
    return out
