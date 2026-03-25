"""
Step 221: In-memory demo data generators. Never persist; never overwrite real data.
All outputs include is_demo: True. Realistic but generic (no fake brand names).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List

# Example demo opportunities (generic product-style titles)
DEMO_OPPORTUNITIES = [
    {"title": "Eco-friendly shipping mailer kit", "score": 78, "priority": "high", "status": "act_now"},
    {"title": "Pet waste pickup telescopic tool", "score": 72, "priority": "medium", "status": "monitor"},
    {"title": "Jewelry shipping protection kit", "score": 68, "priority": "medium", "status": "monitor"},
]

# Demo risk/market signals
DEMO_RISKS = [
    {"risk_type": "competition_risk", "level": "medium", "rationale": "Moderate competition in category."},
    {"risk_type": "saturation_risk", "level": "low", "rationale": "Segment not yet saturated."},
]
DEMO_MARKETS = [
    {"market_key": "DE", "status": "enter_now", "rationale": "Strong demand signals in region."},
    {"market_key": "AU", "status": "monitor", "rationale": "Growing interest; monitor for entry."},
]
DEMO_ALERTS = [
    {"alert_type": "high_potential", "severity": "high", "title": "High-potential opportunity", "description": "Example alert: discovered opportunity meets score threshold."},
    {"alert_type": "trend_signal", "severity": "medium", "title": "Trend signal", "description": "Example: category trend aligns with opportunity."},
]
DEMO_PORTFOLIO_ITEMS = [
    {"item_type": "opportunity", "item_key": "demo-opp-1", "item_label": "Eco-friendly shipping mailer kit", "status": "active"},
    {"item_type": "asin", "item_key": "B0DEMO01", "item_label": "Demo ASIN", "status": "active"},
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_demo_overview(workspace_id: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "total_opportunities": len(DEMO_OPPORTUNITIES),
        "high_priority_opportunities": 1,
        "total_portfolio_items": len(DEMO_PORTFOLIO_ITEMS),
        "high_risk_item_count": 1,
        "top_strategic_score_count": 2,
        "last_updated": _ts(),
    }
    return out


def generate_demo_top_opportunities() -> List[Dict[str, Any]]:
    return [
        {
            "opportunity_id": "demo-%s" % (i + 1),
            "strategy_status": o["status"],
            "priority_level": o["priority"],
            "opportunity_score": float(o["score"]),
            "rationale": "Demo: %s. Strong opportunity score; medium competition." % o["title"],
            "recommended_action": "Review listing and pricing.",
            "risk_notes": [],
            "is_demo": True,
        }
        for i, o in enumerate(DEMO_OPPORTUNITIES)
    ]


def generate_demo_top_risks() -> List[Dict[str, Any]]:
    return [
        {
            "item_key": r.get("risk_type", ""),
            "risk_type": r.get("risk_type", ""),
            "risk_level": r.get("level", "medium"),
            "rationale": r.get("rationale", ""),
            "is_demo": True,
        }
        for r in DEMO_RISKS
    ]


def generate_demo_top_markets() -> List[Dict[str, Any]]:
    return [
        {
            "market_key": m.get("market_key", ""),
            "recommendation_status": m.get("status", "monitor"),
            "rationale": m.get("rationale", ""),
            "is_demo": True,
        }
        for m in DEMO_MARKETS
    ]


def generate_demo_top_recommendations() -> List[Dict[str, Any]]:
    return [
        {"item_key": "demo-rec-1", "priority_level": "high", "rationale": "Add high-scoring opportunity to portfolio.", "is_demo": True},
        {"item_key": "demo-rec-2", "priority_level": "medium", "rationale": "Monitor category for new listings.", "is_demo": True},
    ]


def generate_demo_strategy_summary() -> Dict[str, Any]:
    return {
        "generated_at": _ts(),
        "strategy_summary": {
            "act_now_count": 1,
            "monitor_count": 2,
            "deprioritized_count": 0,
        },
        "is_demo": True,
    }


def generate_demo_risk_summary() -> Dict[str, Any]:
    return {
        "generated_at": _ts(),
        "risk_summary": {"high_risk_count": 1, "medium_risk_count": 1},
        "high_risk_count": 1,
        "is_demo": True,
    }


def generate_demo_market_summary() -> Dict[str, Any]:
    return {
        "generated_at": _ts(),
        "market_entry_summary": {"recommended_markets": ["DE"], "monitor_markets": ["AU"]},
        "is_demo": True,
    }


def generate_demo_portfolio_summary() -> Dict[str, Any]:
    return {
        "total": len(DEMO_PORTFOLIO_ITEMS),
        "active": len(DEMO_PORTFOLIO_ITEMS),
        "archived": 0,
        "is_demo": True,
    }


def generate_demo_dashboard_payload(workspace_id: int) -> Dict[str, Any]:
    """
    Full dashboard-shaped payload with is_demo=True. Same shape as get_dashboard_payload.
    In-memory only; never persisted.
    """
    return {
        "workspace_id": workspace_id,
        "generated_at": _ts(),
        "is_demo": True,
        "overview": generate_demo_overview(workspace_id),
        "intelligence_summary": {"total_tracked_opportunities": len(DEMO_OPPORTUNITIES), "summary_timestamp": _ts(), "is_demo": True},
        "strategy_summary": generate_demo_strategy_summary(),
        "portfolio_summary": generate_demo_portfolio_summary(),
        "risk_summary": generate_demo_risk_summary(),
        "market_summary": generate_demo_market_summary(),
        "activity_summary": {"total_events": 0, "is_demo": True},
        "top_items": {
            "top_opportunities": generate_demo_top_opportunities(),
            "top_recommendations": generate_demo_top_recommendations(),
            "top_risks": generate_demo_top_risks(),
            "top_markets": generate_demo_top_markets(),
        },
        "top_actions": [
            "Review top opportunity: Eco-friendly shipping mailer kit",
            "Monitor DE market entry",
            "Check risk signals in dashboard",
        ],
        "notices": ["Demo mode — data is illustrative and not from your workspace."],
        "health_indicators": {"status": "ok", "demo": True},
    }


def generate_demo_alerts(workspace_id: int) -> List[Dict[str, Any]]:
    """Demo alert records for API list shape. Never persisted."""
    return [
        {
            "id": "demo-alert-%s" % (i + 1),
            "alert_type": a.get("alert_type", ""),
            "severity": a.get("severity", "medium"),
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "recorded_at": _ts(),
            "read_at": None,
            "workspace_id": workspace_id,
            "is_demo": True,
        }
        for i, a in enumerate(DEMO_ALERTS)
    ]


def generate_demo_portfolio_items(workspace_id: int) -> List[Dict[str, Any]]:
    """Demo portfolio list items for API. Never persisted."""
    return [
        {
            "id": "demo-pf-%s" % (i + 1),
            "workspace_id": workspace_id,
            "item_type": p.get("item_type", "opportunity"),
            "item_key": p.get("item_key", ""),
            "item_label": p.get("item_label", ""),
            "source_type": "demo",
            "status": p.get("status", "active"),
            "created_at": _ts(),
            "updated_at": _ts(),
            "is_demo": True,
        }
        for i, p in enumerate(DEMO_PORTFOLIO_ITEMS)
    ]
