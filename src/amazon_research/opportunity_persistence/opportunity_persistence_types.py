"""
Step 236: Opportunity persistence & feed history – payload shape and types.
Stable fields for current vs history; safe for JSONB storage.
"""
from typing import Any, Dict, List, Optional

# Keys we persist in payload_json (subset of feed item; no secrets)
PERSISTED_KEYS = (
    "opportunity_id",
    "title",
    "label",
    "score",
    "opportunity_score",
    "normalized_score",
    "priority_level",
    "priority_band",
    "ranking_position",
    "strategy_status",
    "rationale",
    "recommended_action",
    "risk_notes",
    "supporting_signal_hints",
    "market",
    "category",
    "source_type",
)


def feed_item_to_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extract safe, persistable subset from a feed item. No internal secrets."""
    if not item or not isinstance(item, dict):
        return {}
    out: Dict[str, Any] = {}
    for k in PERSISTED_KEYS:
        if k in item and item[k] is not None:
            v = item[k]
            if isinstance(v, list):
                out[k] = list(v)
            elif isinstance(v, (str, int, float, bool)):
                out[k] = v
            elif v is None:
                pass
            else:
                try:
                    out[k] = str(v)[:500]
                except Exception:
                    pass
    return out


def payload_to_feed_item(payload: Dict[str, Any], observed_at: Optional[str] = None) -> Dict[str, Any]:
    """Turn persisted payload back into a feed-item-like dict. Preserves shape for API."""
    if not payload or not isinstance(payload, dict):
        return {}
    out = dict(payload)
    if observed_at is not None:
        out["observed_at"] = observed_at
    return out
