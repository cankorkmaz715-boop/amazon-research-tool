"""
Step 142: Copilot research planner – turn interpreted research intents into ordered research steps.
Rule-based step sequences; suggested engines per step. Integrates with copilot foundation,
intelligent scanner, opportunity discovery, reverse ASIN, recommendation engine.
Deterministic; extensible for future AI-assisted planning.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.copilot_planner")

# Step types for ordered sequences
STEP_KEYWORD_EXPLORATION = "keyword_exploration"
STEP_KEYWORD_SCAN = "keyword_scan"
STEP_NICHE_DISCOVERY = "niche_discovery"
STEP_CLUSTERING = "clustering"
STEP_OPPORTUNITY_RANKING = "opportunity_ranking"
STEP_REVERSE_ASIN_LOOKUP = "reverse_asin_lookup"
STEP_CONTEXT_EXPANSION = "context_expansion"
STEP_OPPORTUNITY_ANALYSIS = "opportunity_analysis"
STEP_TREND_EXPLORATION = "trend_exploration"

# Engine names (align with research_copilot and discovery modules)
ENGINE_INTELLIGENT_SCANNER = "intelligent_scanner"
ENGINE_KEYWORD_SCAN = "keyword_scan"
ENGINE_NICHE_DISCOVERY = "niche_discovery"
ENGINE_RECOMMENDATION = "recommendation_engine"
ENGINE_ACTION_QUEUE = "action_queue"
ENGINE_TREND = "trend"
ENGINE_REVERSE_ASIN = "reverse_asin"

# Intent -> ordered list of (step_type, [engines for this step])
INTENT_STEP_SEQUENCES = {
    "keyword_exploration": [
        (STEP_KEYWORD_EXPLORATION, [ENGINE_INTELLIGENT_SCANNER]),
        (STEP_KEYWORD_SCAN, [ENGINE_KEYWORD_SCAN, ENGINE_INTELLIGENT_SCANNER]),
        (STEP_NICHE_DISCOVERY, [ENGINE_NICHE_DISCOVERY]),
    ],
    "niche_discovery": [
        (STEP_NICHE_DISCOVERY, [ENGINE_NICHE_DISCOVERY]),
        (STEP_CLUSTERING, [ENGINE_INTELLIGENT_SCANNER]),
        (STEP_OPPORTUNITY_RANKING, [ENGINE_RECOMMENDATION]),
    ],
    "product_opportunity_search": [
        (STEP_REVERSE_ASIN_LOOKUP, [ENGINE_REVERSE_ASIN]),
        (STEP_CONTEXT_EXPANSION, [ENGINE_KEYWORD_SCAN, ENGINE_INTELLIGENT_SCANNER]),
        (STEP_OPPORTUNITY_ANALYSIS, [ENGINE_RECOMMENDATION, ENGINE_ACTION_QUEUE]),
    ],
    "trend_exploration": [
        (STEP_TREND_EXPLORATION, [ENGINE_TREND]),
        (STEP_KEYWORD_SCAN, [ENGINE_KEYWORD_SCAN]),
        (STEP_OPPORTUNITY_RANKING, [ENGINE_RECOMMENDATION]),
    ],
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rationale_for_intent(intent: str) -> str:
    """Short planning rationale per intent."""
    if intent == "keyword_exploration":
        return "Keyword exploration → keyword scan → niche discovery; expand terms then discover niches."
    if intent == "niche_discovery":
        return "Niche discovery → clustering → opportunity ranking; find clusters then rank opportunities."
    if intent == "product_opportunity_search":
        return "Reverse ASIN lookup → context expansion → opportunity analysis; start from products then expand and analyze."
    if intent == "trend_exploration":
        return "Trend exploration → keyword scan → opportunity ranking; identify trends then rank opportunities."
    return "Default sequence for intent."


def build_research_plan(
    copilot_output: Optional[Dict[str, Any]] = None,
    *,
    interpreted_intent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Turn interpreted research intent into an ordered research plan. Uses copilot_output
    (from interpret_query) or explicit interpreted_intent. Returns: plan_id, interpreted_intent,
    ordered_research_steps (list of { step_order, step_type, suggested_engines }), suggested_engines_per_step
    (alias), planning_rationale_summary, timestamp.
    """
    intent = interpreted_intent
    if intent is None and copilot_output:
        intent = (copilot_output.get("interpreted_intent") or (copilot_output.get("research_plan_summary") or {}).get("intent") or "").strip()
    if not intent:
        intent = "niche_discovery"
    plan_id = f"plan-{uuid.uuid4().hex[:12]}"
    now = _ts()
    sequence = INTENT_STEP_SEQUENCES.get(intent) or INTENT_STEP_SEQUENCES["niche_discovery"]
    ordered_steps: List[Dict[str, Any]] = []
    for i, (step_type, engines) in enumerate(sequence, start=1):
        ordered_steps.append({
            "step_order": i,
            "step_type": step_type,
            "suggested_engines": list(engines),
        })
    rationale = _rationale_for_intent(intent)
    return {
        "plan_id": plan_id,
        "interpreted_intent": intent,
        "ordered_research_steps": ordered_steps,
        "suggested_engines_per_step": ordered_steps,
        "planning_rationale_summary": rationale,
        "timestamp": now,
    }


def get_plan_for_query(query: str) -> Dict[str, Any]:
    """
    Convenience: interpret query via copilot then build plan. Returns full plan output.
    """
    from amazon_research.discovery import interpret_query
    copilot_output = interpret_query(query)
    return build_research_plan(copilot_output)
