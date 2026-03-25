"""
Step 141: Research copilot layer (foundation) – interpret natural language research queries
and convert them into structured research tasks. Rule-based, no external AI in this step.
Extensible for future AI-powered copilots.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.research_copilot")

INTENT_NICHE_DISCOVERY = "niche_discovery"
INTENT_PRODUCT_OPPORTUNITY = "product_opportunity_search"
INTENT_KEYWORD_EXPLORATION = "keyword_exploration"
INTENT_TREND_EXPLORATION = "trend_exploration"

ENTITY_KEYWORD = "keyword"
ENTITY_NICHE = "niche"
ENTITY_PRODUCT = "product"

ENGINE_NICHE_DISCOVERY = "niche_discovery"
ENGINE_INTELLIGENT_SCANNER = "intelligent_scanner"
ENGINE_RECOMMENDATION = "recommendation_engine"
ENGINE_ACTION_QUEUE = "action_queue"
ENGINE_KEYWORD_SCAN = "keyword_scan"
ENGINE_TREND = "trend"

# Rule-based triggers (lowercase); first match wins for intent
INTENT_TRIGGERS = [
    (INTENT_NICHE_DISCOVERY, ["niche", "niches", "discover niche", "find niches", "cluster", "segment"]),
    (INTENT_PRODUCT_OPPORTUNITY, ["opportunity", "opportunities", "product opportunity", "market opportunity", "best products to sell"]),
    (INTENT_KEYWORD_EXPLORATION, ["keyword", "keywords", "explore keyword", "keyword research", "search term"]),
    (INTENT_TREND_EXPLORATION, ["trend", "trends", "trending", "trend exploration", "market trend"]),
]

# Market hints (optional extraction)
MARKET_PATTERNS = [
    (r"\b(?:in|for|market)\s+(?:us|usa|united states)\b", "US"),
    (r"\b(?:in|for|market)\s+(?:uk|gb|united kingdom)\b", "UK"),
    (r"\b(?:in|for|market)\s+(?:de|germany)\b", "DE"),
    (r"\b(?:in|for|market)\s+(?:amazon\.)?(com|co\.uk|de)\b", None),  # normalize below
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _interpret_intent(query: str) -> str:
    """Rule-based: return first matching intent from INTENT_TRIGGERS, else niche_discovery as default."""
    q = (query or "").strip().lower()
    if not q:
        return INTENT_NICHE_DISCOVERY
    for intent, triggers in INTENT_TRIGGERS:
        for t in triggers:
            if t in q:
                return intent
    return INTENT_NICHE_DISCOVERY


def _extract_target_market(query: str) -> Optional[str]:
    """Optional: extract market from query using MARKET_PATTERNS."""
    q = (query or "").strip()
    for pattern, market in MARKET_PATTERNS:
        m = re.search(pattern, q, re.IGNORECASE)
        if m:
            if market:
                return market
            g = m.group(1) if m.lastindex else ""
            if "com" in g.lower():
                return "US"
            if "uk" in g.lower():
                return "UK"
            if "de" in g.lower():
                return "DE"
    return None


def _intent_to_entity_type(intent: str) -> str:
    """Map interpreted intent to candidate entity type."""
    if intent == INTENT_KEYWORD_EXPLORATION:
        return ENTITY_KEYWORD
    if intent == INTENT_PRODUCT_OPPORTUNITY:
        return ENTITY_PRODUCT
    if intent in (INTENT_NICHE_DISCOVERY, INTENT_TREND_EXPLORATION):
        return ENTITY_NICHE
    return ENTITY_NICHE


def _intent_to_engines(intent: str) -> List[str]:
    """Map intent to recommended research engines to run."""
    if intent == INTENT_NICHE_DISCOVERY:
        return [ENGINE_NICHE_DISCOVERY, ENGINE_INTELLIGENT_SCANNER]
    if intent == INTENT_PRODUCT_OPPORTUNITY:
        return [ENGINE_RECOMMENDATION, ENGINE_ACTION_QUEUE, ENGINE_INTELLIGENT_SCANNER]
    if intent == INTENT_KEYWORD_EXPLORATION:
        return [ENGINE_INTELLIGENT_SCANNER, ENGINE_KEYWORD_SCAN]
    if intent == INTENT_TREND_EXPLORATION:
        return [ENGINE_TREND, ENGINE_INTELLIGENT_SCANNER]
    return [ENGINE_INTELLIGENT_SCANNER]


def interpret_query(query: str) -> Dict[str, Any]:
    """
    Interpret a natural language research query and produce a structured research plan.
    Returns: copilot_request_id, interpreted_intent, research_plan_summary (intent, target_market,
    entity_type, engines_suggested), engines_suggested (list), timestamp.
    Rule-based; no external AI. Integrates conceptually with opportunity discovery,
    intelligent scanner, recommendation engine, action queue.
    """
    request_id = f"copilot-{uuid.uuid4().hex[:12]}"
    intent = _interpret_intent(query)
    target_market = _extract_target_market(query)
    entity_type = _intent_to_entity_type(intent)
    engines = _intent_to_engines(intent)
    now = _ts()
    plan_summary = {
        "intent": intent,
        "target_market": target_market,
        "entity_type": entity_type,
        "engines_suggested": engines,
    }
    return {
        "copilot_request_id": request_id,
        "interpreted_intent": intent,
        "research_plan_summary": plan_summary,
        "engines_suggested": engines,
        "timestamp": now,
    }


def plan_to_action_hints(copilot_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert copilot output into a list of suggested action hints for the action queue / executor.
    Does not enqueue; returns structured hints (engine, entity_type, intent) for downstream use.
    """
    plan = copilot_output.get("research_plan_summary") or {}
    engines = copilot_output.get("engines_suggested") or []
    intent = plan.get("intent") or copilot_output.get("interpreted_intent")
    entity_type = plan.get("entity_type") or ENTITY_NICHE
    hints = []
    for eng in engines:
        hints.append({
            "engine": eng,
            "entity_type": entity_type,
            "intent": intent,
        })
    return hints
