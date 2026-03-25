"""
Step 224: Basic usage analytics layer. Lightweight, production-safe event tracking.
"""
from amazon_research.usage_analytics.collector import record_analytics_event
from amazon_research.usage_analytics.events import (
    ALLOWED_ACTIONS,
    ALLOWED_EVENTS,
    ALLOWED_PAGE_VIEWS,
    is_allowed_event,
)

__all__ = [
    "record_analytics_event",
    "is_allowed_event",
    "ALLOWED_EVENTS",
    "ALLOWED_PAGE_VIEWS",
    "ALLOWED_ACTIONS",
]
