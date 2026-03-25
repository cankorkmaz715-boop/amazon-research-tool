"""
Workspace-scoped API keys. Step 51 – tenant auth; keys stored hashed; multiple per workspace.
"""
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Tuple

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.workspace_api_keys")


def _hash_key(plaintext: str) -> str:
    """Return SHA-256 hex digest of the key (normalized)."""
    return hashlib.sha256((plaintext or "").strip().encode("utf-8")).hexdigest()


def create_workspace_api_key(
    workspace_id: int,
    label: Optional[str] = None,
    secret: Optional[str] = None,
) -> Tuple[str, int]:
    """
    Create a new API key for the workspace. Keys are stored hashed.
    Returns (plaintext_secret, key_id). Caller must store plaintext_secret; it is not stored.
    If secret is provided it is used; otherwise a random 32-byte hex key is generated.
    """
    conn = get_connection()
    cur = conn.cursor()
    plaintext = (secret or "").strip() or secrets.token_hex(32)
    key_hash = _hash_key(plaintext)
    label_val = (label or "").strip() or None
    cur.execute(
        """
        INSERT INTO workspace_api_keys (workspace_id, key_hash, label)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (workspace_id, key_hash, label_val),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return plaintext, row[0]


def validate_workspace_api_key(plaintext: str) -> Optional[int]:
    """
    Validate a workspace API key. Returns workspace_id if the key is valid, else None.
    """
    if not (plaintext or "").strip():
        return None
    key_hash = _hash_key(plaintext)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT workspace_id FROM workspace_api_keys WHERE key_hash = %s",
        (key_hash,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def list_workspace_api_keys(workspace_id: int) -> List[Dict[str, Any]]:
    """List API key metadata for the workspace (no key or hash returned)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, label, created_at
        FROM workspace_api_keys
        WHERE workspace_id = %s
        ORDER BY created_at DESC
        """,
        (workspace_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"id": r[0], "label": r[1], "created_at": r[2]}
        for r in rows
    ]
