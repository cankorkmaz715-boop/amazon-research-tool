"""
Step 221: Demo data mode. In-memory demo payloads for empty workspaces; never persisted.
"""
from amazon_research.demo_data.config import is_demo_mode_enabled
from amazon_research.demo_data.generators import (
    generate_demo_alerts,
    generate_demo_dashboard_payload,
    generate_demo_portfolio_items,
)
from amazon_research.demo_data.resolver import (
    should_use_demo_for_alerts,
    should_use_demo_for_dashboard,
    should_use_demo_for_portfolio,
)

__all__ = [
    "is_demo_mode_enabled",
    "generate_demo_dashboard_payload",
    "generate_demo_alerts",
    "generate_demo_portfolio_items",
    "should_use_demo_for_dashboard",
    "should_use_demo_for_alerts",
    "should_use_demo_for_portfolio",
]
