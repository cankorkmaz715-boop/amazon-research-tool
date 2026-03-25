"""
Step 234: Real opportunity feed engine – source real opportunities from pipeline for dashboard and API.
"""
from amazon_research.opportunity_feed.opportunity_feed_service import (
    get_real_opportunity_feed,
    get_opportunity_feed_for_dashboard,
)
from amazon_research.opportunity_feed.opportunity_feed_types import (
    SOURCE_REAL,
    SOURCE_DEMO,
    stable_feed_item,
    empty_feed_item,
)

__all__ = [
    "get_real_opportunity_feed",
    "get_opportunity_feed_for_dashboard",
    "SOURCE_REAL",
    "SOURCE_DEMO",
    "stable_feed_item",
    "empty_feed_item",
]
