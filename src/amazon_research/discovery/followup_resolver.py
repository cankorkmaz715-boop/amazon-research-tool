"""
Step 147: Follow-up research resolver – map a new copilot query to the most relevant prior thread/session.
Supports same-niche, same-ASIN/product/cluster, market-specific, and similar/related/compare/continue patterns.
Rule-based, explainable. Uses conversational threading and copilot research memory.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.followup_resolver")

# Follow-up type constants
FOLLOWUP_SAME_NICHE = "same_niche_continuation"
FOLLOWUP_SAME_ASIN_PRODUCT_CLUSTER = "same_asin_product_cluster"
FOLLOWUP_MARKET_SPECIFIC = "market_specific_followup"
FOLLOWUP_SIMILAR_RELATED_COMPARE = "similar_related_compare_continue"
FOLLOWUP_NONE = "none"

# Trigger phrases (lowercase) that suggest follow-up intent
FOLLOWUP_TRIGGERS = [
    "same", "continue", "follow up", "follow-up", "that", "similar", "related", "compare",
    "more", "again", "same niche", "same product", "that asin", "that product", "that cluster",
    "further", "deeper", "expand", "previous", "last time", "earlier",
]

# Keywords that hint at follow-up type (for classification)
NICHE_HINTS = ["niche", "niches", "segment", "cluster", "category"]
ASIN_PRODUCT_HINTS = ["asin", "product", "item", "listing", "cluster"]
MARKET_HINTS = ["market", "us", "uk", "de", "amazon.com", "region"]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _query_has_followup_intent(query: str) -> bool:
    """True if query contains follow-up style language."""
    q = (query or "").strip().lower()
    for t in FOLLOWUP_TRIGGERS:
        if t in q:
            return True
    return False


def _classify_followup_type(query: str) -> str:
    """Classify follow-up type from query keywords. Rule-based."""
    q = (query or "").strip().lower()
    if any(h in q for h in NICHE_HINTS):
        return FOLLOWUP_SAME_NICHE
    if any(h in q for h in ASIN_PRODUCT_HINTS):
        return FOLLOWUP_SAME_ASIN_PRODUCT_CLUSTER
    if any(h in q for h in MARKET_HINTS):
        return FOLLOWUP_MARKET_SPECIFIC
    if _query_has_followup_intent(q):
        return FOLLOWUP_SIMILAR_RELATED_COMPARE
    return FOLLOWUP_NONE


def _word_overlap(a: str, b: str) -> int:
    """Count overlapping words (normalized, no duplicates)."""
    if not a or not b:
        return 0
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    return len(wa & wb)


def _score_thread_match(
    query: str,
    current_intent: str,
    thread: Dict[str, Any],
    summary: Optional[Dict[str, Any]],
) -> Tuple[float, str]:
    """Score a thread against the query. Returns (score 0–100, rationale)."""
    topic = (thread.get("thread_topic") or "") or (summary.get("thread_summary") if summary else "") or ""
    anchor = (thread.get("thread_anchor") or "") or ""
    text = f"{topic} {anchor}".strip()
    overlap = _word_overlap(query, text)
    intent_match = 0.0
    if summary and summary.get("thread_topic"):
        # Infer intent from first session if we had it; for now use topic overlap
        intent_match = 10.0 if overlap > 0 else 0.0
    anchor_bonus = (15 if anchor and overlap > 0 else 0)
    score = min(100, overlap * 8 + intent_match + anchor_bonus)
    rationale = f"topic/anchor overlap={overlap}"
    if anchor:
        rationale += ", anchor present"
    return (score, rationale)


def _score_session_match(
    query: str,
    current_intent: str,
    session: Dict[str, Any],
) -> Tuple[float, str]:
    """Score a session against the query. Returns (score 0–100, rationale)."""
    prior_query = (session.get("copilot_query") or "").strip()
    prior_intent = (session.get("interpreted_intent") or "").strip()
    overlap = _word_overlap(query, prior_query)
    intent_match = 20.0 if prior_intent and prior_intent == current_intent else 0.0
    score = min(100, overlap * 6 + intent_match + (10 if prior_query else 0))
    rationale = f"query overlap={overlap}"
    if intent_match:
        rationale += ", intent match"
    return (score, rationale)


def resolve_followup(
    query: str,
    *,
    workspace_id: Optional[int] = None,
    limit_threads: int = 20,
    limit_sessions: int = 30,
    prefer_thread: bool = True,
) -> Dict[str, Any]:
    """
    Map a new copilot query to the most relevant prior research thread or session when appropriate.
    Returns: resolver_result_id, matched_thread_id (optional), matched_session_id (optional),
    follow_up_type, confidence/rationale, timestamp. If no match, follow_up_type is FOLLOWUP_NONE.
    """
    result_id = f"resolve-{uuid.uuid4().hex[:12]}"
    q = (query or "").strip()
    out: Dict[str, Any] = {
        "resolver_result_id": result_id,
        "matched_thread_id": None,
        "matched_session_id": None,
        "follow_up_type": FOLLOWUP_NONE,
        "match_rationale": "",
        "confidence": 0,
        "timestamp": _ts(),
    }

    # Current intent from copilot
    current_intent = ""
    try:
        from amazon_research.discovery.research_copilot import interpret_query
        interp = interpret_query(q)
        current_intent = (interp.get("interpreted_intent") or "").strip()
    except Exception as e:
        logger.debug("resolve_followup interpret_query: %s", e)

    follow_up_type = _classify_followup_type(q)
    out["follow_up_type"] = follow_up_type

    best_score = 0.0
    best_rationale = ""
    best_thread_id: Optional[str] = None
    best_session_id: Optional[str] = None

    # Consider threads first if prefer_thread
    if prefer_thread:
        try:
            from amazon_research.discovery.conversational_threading import list_threads, get_thread_summary
            threads = list_threads(workspace_id=workspace_id, limit=limit_threads)
            for t in threads:
                tid = t.get("thread_id")
                if not tid:
                    continue
                summary = get_thread_summary(tid, workspace_id=workspace_id)
                score, rationale = _score_thread_match(q, current_intent, t, summary)
                if score > best_score:
                    best_score = score
                    best_rationale = rationale
                    best_thread_id = tid
                    best_session_id = None
        except Exception as e:
            logger.debug("resolve_followup list_threads: %s", e)

    # Consider sessions (standalone or when no thread beat threshold)
    try:
        from amazon_research.discovery.copilot_research_memory import list_sessions
        sessions = list_sessions(workspace_id=workspace_id, limit=limit_sessions)
        for s in sessions:
            sid = s.get("session_id")
            if not sid:
                continue
            score, rationale = _score_session_match(q, current_intent, s)
            if score > best_score:
                best_score = score
                best_rationale = rationale
                best_thread_id = None
                best_session_id = sid
    except Exception as e:
        logger.debug("resolve_followup list_sessions: %s", e)

    # Require minimum score to report a match (avoid false positives; need some topic/query overlap)
    if best_score >= 12.0:
        out["matched_thread_id"] = best_thread_id
        out["matched_session_id"] = best_session_id
        out["confidence"] = min(100, int(best_score))
        out["match_rationale"] = best_rationale
    else:
        out["follow_up_type"] = FOLLOWUP_NONE
        out["match_rationale"] = "no prior thread or session scored above threshold"

    return out


def resolve_followup_to_session_or_thread(
    query: str,
    *,
    workspace_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Convenience: return the single best match (thread or session) for the query, or None.
    Returns same structure as resolve_followup but only when there is a match.
    """
    r = resolve_followup(query, workspace_id=workspace_id)
    if r.get("matched_thread_id") or r.get("matched_session_id"):
        return r
    return None
