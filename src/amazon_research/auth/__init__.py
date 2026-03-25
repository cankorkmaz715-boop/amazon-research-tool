"""
Internal access control. Step 46 – lightweight API key + workspace scoping.
"""
from .internal import validate_internal_request

__all__ = ["validate_internal_request"]
