"""
Step 240: Discovery-to-opportunity conversion. Workspace-scoped; uses opportunity_memory.
"""
from amazon_research.opportunity_conversion.discovery_to_opportunity_service import (
    convert_discovery_to_opportunity,
)
from amazon_research.opportunity_conversion.discovery_conversion_types import (
    STATUS_CREATED,
    STATUS_UPDATED,
    STATUS_FAILED,
    conversion_response,
)

__all__ = [
    "convert_discovery_to_opportunity",
    "STATUS_CREATED",
    "STATUS_UPDATED",
    "STATUS_FAILED",
    "conversion_response",
]
