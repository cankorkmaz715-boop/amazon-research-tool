"""Pipeline: Opportunity detail for GET /opportunities/{id}."""
from amazon_research.opportunity_detail.opportunity_detail_service import (
    get_opportunity_detail,
    get_opportunity_ref_by_id,
)

__all__ = ["get_opportunity_detail", "get_opportunity_ref_by_id"]
