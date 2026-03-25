"""
Step 224: Basic usage analytics – non-blocking event recording.
Uses existing workspace_usage_events via record_usage; event_type prefixed with analytics:.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

from .events import is_allowed_event

logger = get_logger("usage_analytics.collector")

# Prefix so analytics events are distinct in workspace_usage_events
EVENT_TYPE_PREFIX = "analytics:"

# Max keys in metadata to avoid large payloads
MAX_META_KEYS = 10


def _sanitize_metadata(meta: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return a safe subset of metadata: only string/number/boolean values, no nested objects."""
    if not meta or not isinstance(meta, dict):
        return None
    out: Dict[str, Any] = {}
    for k, v in list(meta.items())[:MAX_META_KEYS]:
        if not isinstance(k, str) or len(k) > 64:
            continue
        if v is None or isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, (list, dict)):
            continue  # skip nested to avoid sensitive dumps
    return out if out else None


def record_analytics_event(
    workspace_id: Optional[int],
    event_name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Record a usage analytics event. Non-blocking; logs warning on failure.
    Returns True if recorded, False if skipped or failed.
    """
    name = (event_name or "").strip()
    if not is_allowed_event(name):
        logger.warning("usage_analytics event not in allowlist: %s", name)
        return False
    try:
        from amazon_research.db import record_usage
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "meta": _sanitize_metadata(metadata),
        }
        event_type = EVENT_TYPE_PREFIX + name
        record_usage(workspace_id=workspace_id, event_type=event_type, payload=payload)
        return True
    except Exception as e:
        logger.warning("usage_analytics record failed event=%s: %s", name, e)
        return False
