"""
Step 240: Map discovery conversion payload to opportunity_ref and context.
Workspace-scoped ref to avoid cross-workspace collisions in opportunity_memory.
"""
import re
from typing import Any, Dict, Optional

from amazon_research.opportunity_conversion.discovery_conversion_types import (
    KEY_CATEGORY,
    KEY_DISCOVERY_ID,
    KEY_KEYWORD,
    KEY_MARKET,
    KEY_SOURCE_METADATA,
)

REF_PREFIX_KW = "kw"
MAX_REF_LEN = 200


def _normalize_keyword(keyword: Optional[str]) -> str:
    if not keyword:
        return ""
    s = (keyword or "").strip()
    s = re.sub(r"\s+", "_", s)[:150]
    return s or ""


def build_opportunity_ref(
    workspace_id: int,
    keyword: Optional[str] = None,
    market: Optional[str] = None,
    discovery_id: Optional[str] = None,
) -> str:
    """
    Build a stable, workspace-scoped opportunity_ref for discovery conversion.
    Uses discovery_id if provided and non-empty; else w{workspace_id}:{market}:kw:{keyword}.
    """
    market_clean = (market or "DE").strip().upper() or "DE"
    if discovery_id and (discovery_id or "").strip():
        ref = (discovery_id or "").strip()[:MAX_REF_LEN]
        return f"w{workspace_id}:{ref}"
    kw = _normalize_keyword(keyword)
    if not kw:
        kw = "unknown"
    return f"w{workspace_id}:{market_clean}:{REF_PREFIX_KW}:{kw}"


def build_context(
    keyword: Optional[str] = None,
    market: Optional[str] = None,
    category: Optional[str] = None,
    discovery_id: Optional[str] = None,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build context dict for opportunity_memory record."""
    ctx: Dict[str, Any] = {
        "source_type": "discovery_conversion",
        "keyword": (keyword or "").strip() or None,
        "market": (market or "DE").strip().upper() or "DE",
    }
    if category and (category or "").strip():
        ctx["category"] = (category or "").strip()
    if discovery_id and (discovery_id or "").strip():
        ctx["discovery_id"] = (discovery_id or "").strip()
    if source_metadata and isinstance(source_metadata, dict):
        ctx["source_metadata"] = dict(source_metadata)
    return ctx
