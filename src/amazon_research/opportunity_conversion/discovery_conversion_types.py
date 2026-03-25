"""
Step 240: Discovery-to-opportunity conversion – request/response types.
"""
from typing import Any, Dict, Optional

# Request body keys
KEY_DISCOVERY_ID = "discovery_id"
KEY_KEYWORD = "keyword"
KEY_MARKET = "market"
KEY_CATEGORY = "category"
KEY_SOURCE_METADATA = "source_metadata"

# Response keys
KEY_OPPORTUNITY_ID = "opportunity_id"
KEY_STATUS = "status"
KEY_MESSAGE = "message"

STATUS_CREATED = "created"
STATUS_UPDATED = "updated"
STATUS_FAILED = "failed"


def conversion_request(
    discovery_id: Optional[str] = None,
    keyword: Optional[str] = None,
    market: Optional[str] = None,
    category: Optional[str] = None,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        KEY_DISCOVERY_ID: discovery_id,
        KEY_KEYWORD: keyword,
        KEY_MARKET: market,
        KEY_CATEGORY: category,
        KEY_SOURCE_METADATA: dict(source_metadata or {}),
    }


def conversion_response(
    opportunity_id: Optional[int] = None,
    status: str = STATUS_FAILED,
    message: str = "",
) -> Dict[str, Any]:
    return {
        KEY_OPPORTUNITY_ID: opportunity_id,
        KEY_STATUS: status,
        KEY_MESSAGE: message or "",
    }
