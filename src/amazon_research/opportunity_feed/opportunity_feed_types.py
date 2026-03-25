"""
Step 234: Real opportunity feed – type constants and stable item shape.
"""
from typing import Any, Dict, List, Optional

SOURCE_REAL = "real"
SOURCE_DEMO = "demo"

# Stable feed item keys for dashboard/API (do not break payload shape)
FEED_ITEM_KEYS = (
    "opportunity_id",
    "title",
    "label",
    "score",
    "priority_level",
    "strategy_status",
    "rationale",
    "recommended_action",
    "risk_notes",
    "market",
    "category",
    "source_type",
)


def empty_feed_item(opportunity_id: str = "") -> Dict[str, Any]:
    """Single placeholder for empty-state; not used when real items exist."""
    return {
        "opportunity_id": opportunity_id,
        "title": "",
        "label": "",
        "score": None,
        "priority_level": "low",
        "strategy_status": "monitor",
        "rationale": "",
        "recommended_action": "",
        "risk_notes": [],
        "market": None,
        "category": None,
        "source_type": SOURCE_REAL,
    }


def stable_feed_item(
    opportunity_id: str,
    *,
    title: str = "",
    label: str = "",
    score: Optional[float] = None,
    priority_level: str = "medium",
    strategy_status: str = "monitor",
    rationale: str = "",
    recommended_action: str = "",
    risk_notes: List[Any] = None,
    market: str = None,
    category: str = None,
    source_type: str = SOURCE_REAL,
) -> Dict[str, Any]:
    """Build one feed item with stable keys for API/dashboard."""
    return {
        "opportunity_id": opportunity_id,
        "title": (title or "")[:200],
        "label": (label or "")[:200],
        "score": float(score) if score is not None else None,
        "priority_level": priority_level or "medium",
        "strategy_status": strategy_status or "monitor",
        "rationale": (rationale or "")[:500],
        "recommended_action": (recommended_action or "")[:200],
        "risk_notes": list(risk_notes) if risk_notes else [],
        "market": market,
        "category": category,
        "source_type": source_type or SOURCE_REAL,
    }
