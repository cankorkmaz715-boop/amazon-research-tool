"""
Step 224: Basic usage analytics – allowed event names. No sensitive payloads.
"""
from typing import Set

# Page view events (safe, non-sensitive)
ALLOWED_PAGE_VIEWS: Set[str] = {
    "workspace_dashboard_viewed",
    "portfolio_page_viewed",
    "alerts_page_viewed",
    "workspace_creation_viewed",
    "onboarding_viewed",
}

# Action events (safe, non-sensitive)
ALLOWED_ACTIONS: Set[str] = {
    "walkthrough_started",
    "walkthrough_completed",
    "onboarding_completed",
    "workspace_created",
    "portfolio_item_archived",
    "alert_marked_read",
    "demo_mode_seen",
}

ALLOWED_EVENTS: Set[str] = ALLOWED_PAGE_VIEWS | ALLOWED_ACTIONS


def is_allowed_event(event_name: str) -> bool:
    """Return True if event_name is in the allowlist."""
    return (event_name or "").strip() in ALLOWED_EVENTS
