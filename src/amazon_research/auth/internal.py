"""
Internal auth – validate API key and optional workspace scope. Step 46.
Step 51: workspace-scoped API keys supported; INTERNAL_API_KEY retained for internal tools.
"""
from typing import Any, Dict, Optional, Tuple

from amazon_research.logging_config import get_logger
from amazon_research.config import get_config

logger = get_logger("auth")


def _get_header(headers: Optional[Dict[str, str]], hdr: str) -> Optional[str]:
    if not headers:
        return None
    for k, v in headers.items():
        if k.lower().replace("_", "-") == hdr.lower():
            return (v or "").strip()
    return None


def validate_internal_request(
    headers: Optional[Dict[str, str]] = None,
    api_key: Optional[str] = None,
    workspace_id_header: Optional[str] = None,
) -> Tuple[bool, Optional[int]]:
    """
    Validate internal API request. Returns (allowed, workspace_id or None).
    Accepts INTERNAL_API_KEY (global) or a valid workspace API key (resolves workspace_id from DB).
    If INTERNAL_API_KEY is not set, allows unauthenticated or workspace-key auth.
    """
    cfg = get_config()
    internal_key = getattr(cfg, "internal_api_key", None) and (cfg.internal_api_key or "").strip()

    provided_key: Optional[str] = None
    if api_key:
        provided_key = api_key.strip()
    elif headers:
        provided_key = _get_header(headers, "X-API-Key") or ""
        if not provided_key:
            auth = _get_header(headers, "Authorization") or ""
            if auth.lower().startswith("bearer "):
                provided_key = auth[7:].strip()

    # INTERNAL_API_KEY: allow and use X-Workspace-Id for scope
    if internal_key and provided_key and provided_key == internal_key:
        workspace_id = None
        raw_ws = workspace_id_header or (headers and _get_header(headers, "X-Workspace-Id"))
        if raw_ws:
            try:
                workspace_id = int(str(raw_ws).strip())
            except (TypeError, ValueError):
                pass
            if workspace_id is not None:
                from amazon_research.db import get_workspace
                if get_workspace(workspace_id) is None:
                    return False, None
        return True, workspace_id

    # Workspace API key: resolve workspace_id from DB
    if provided_key:
        from amazon_research.db import validate_workspace_api_key
        ws_id = validate_workspace_api_key(provided_key)
        if ws_id is not None:
            return True, ws_id

    # No key required (internal key not set): allow; optional workspace from header
    if not internal_key:
        workspace_id = None
        raw_ws = workspace_id_header or (headers and _get_header(headers, "X-Workspace-Id"))
        if raw_ws:
            try:
                workspace_id = int(str(raw_ws).strip())
            except (TypeError, ValueError):
                pass
            if workspace_id is not None:
                from amazon_research.db import get_workspace
                if get_workspace(workspace_id) is None:
                    return False, None
        return True, workspace_id

    return False, None
