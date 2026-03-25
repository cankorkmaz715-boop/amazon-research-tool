"""
Step 240: Convert discovery result into opportunity record.
Uses opportunity_memory (record_opportunity_seen); workspace-scoped; duplicate = upsert.
"""
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

from amazon_research.opportunity_conversion.discovery_conversion_types import (
    KEY_CATEGORY,
    KEY_DISCOVERY_ID,
    KEY_KEYWORD,
    KEY_MARKET,
    KEY_SOURCE_METADATA,
    STATUS_CREATED,
    STATUS_FAILED,
    STATUS_UPDATED,
    conversion_response,
)
from amazon_research.opportunity_conversion.discovery_conversion_mapper import (
    build_opportunity_ref,
    build_context,
)

logger = get_logger("opportunity_conversion.service")


def _get_existing_ref(workspace_id: int, ref: str) -> Optional[int]:
    """Return opportunity_memory id if a row exists for this ref and workspace."""
    try:
        from amazon_research.db.opportunity_memory import get_opportunity_memory
        row = get_opportunity_memory(ref)
        if row and row.get("workspace_id") == workspace_id:
            return row.get("id")
    except Exception:
        pass
    return None


def convert_discovery_to_opportunity(
    workspace_id: int,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create or update opportunity from discovery payload.
    Payload: discovery_id?, keyword, market, category?, source_metadata?.
    Returns: opportunity_id, status (created|updated|failed), message.
    """
    keyword = (payload.get(KEY_KEYWORD) or "").strip() or None
    market = (payload.get(KEY_MARKET) or "").strip() or None
    discovery_id = (payload.get(KEY_DISCOVERY_ID) or "").strip() or None
    category = (payload.get(KEY_CATEGORY) or "").strip() or None
    source_metadata = payload.get(KEY_SOURCE_METADATA)
    if isinstance(source_metadata, dict):
        source_metadata = source_metadata
    else:
        source_metadata = None

    if not keyword and not discovery_id:
        logger.warning("discovery_conversion missing keyword and discovery_id workspace_id=%s", workspace_id)
        return conversion_response(status=STATUS_FAILED, message="keyword or discovery_id required")

    ref = build_opportunity_ref(workspace_id, keyword=keyword, market=market, discovery_id=discovery_id)
    if not ref:
        return conversion_response(status=STATUS_FAILED, message="invalid ref")

    context = build_context(
        keyword=keyword,
        market=market,
        category=category,
        discovery_id=discovery_id,
        source_metadata=source_metadata,
    )
    existed_before = _get_existing_ref(workspace_id, ref) is not None

    try:
        from amazon_research.db.opportunity_memory import record_opportunity_seen
        row_id = record_opportunity_seen(
            ref,
            context=context,
            latest_opportunity_score=None,
            workspace_id=workspace_id,
        )
    except Exception as e:
        logger.warning(
            "discovery_conversion failed workspace_id=%s ref=%s: %s",
            workspace_id,
            ref[:50],
            e,
            extra={"workspace_id": workspace_id},
        )
        return conversion_response(status=STATUS_FAILED, message=str(e))

    if row_id is None:
        return conversion_response(status=STATUS_FAILED, message="record_opportunity_seen returned None")

    status = STATUS_UPDATED if existed_before else STATUS_CREATED
    logger.info(
        "discovery_conversion %s workspace_id=%s opportunity_id=%s ref=%s",
        status,
        workspace_id,
        row_id,
        ref[:60],
        extra={"workspace_id": workspace_id, "opportunity_id": row_id},
    )
    return conversion_response(
        opportunity_id=row_id,
        status=status,
        message=f"Opportunity {status}",
    )
