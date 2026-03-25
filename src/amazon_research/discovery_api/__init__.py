"""
Step 238: Real market/keyword discovery API. Reuses runtime discovery outputs; workspace-scoped.
"""
from amazon_research.discovery_api.discovery_service import (
    get_keyword_discovery,
    get_market_discovery,
    get_category_discovery,
    get_discovery_summary,
)
from amazon_research.discovery_api.discovery_types import (
    empty_keyword_result,
    empty_market_result,
    empty_category_result,
)

__all__ = [
    "get_keyword_discovery",
    "get_market_discovery",
    "get_category_discovery",
    "get_discovery_summary",
    "empty_keyword_result",
    "empty_market_result",
    "empty_category_result",
]
