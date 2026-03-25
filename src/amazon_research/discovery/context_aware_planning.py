"""
Step 148: Context-aware research planning – extend copilot planner with prior conversational/research context.
Uses matched thread/session, prior intent, plan, insight summary, next steps, niche/cluster/market.
Distinguishes fresh vs follow-up requests. Rule-based, explainable.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.context_aware_planning")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_context_aware_plan(
    query: str,
    *,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a research plan that incorporates prior context when available (matched thread/session,
    prior intent, plan, insight summary, next steps, niche/cluster/market). Distinguishes fresh vs
    follow-up/continuation. Returns: plan_id, source_query, context_references_used,
    ordered_research_steps, planning_rationale, timestamp, plus interpreted_intent, is_follow_up.
    """
    source_query = (query or "").strip()
    context_refs: Dict[str, Any] = {
        "matched_thread_id": None,
        "matched_session_id": None,
        "prior_interpreted_intent": None,
        "prior_research_plan_ref": None,
        "prior_insight_summary_ref": None,
        "prior_recommended_next_steps_ref": None,
        "prior_niche_cluster_market": None,
    }

    # 1) Interpret current query
    current_intent = "niche_discovery"
    try:
        from amazon_research.discovery import interpret_query
        interp = interpret_query(source_query)
        current_intent = (interp.get("interpreted_intent") or "niche_discovery").strip()
    except Exception as e:
        logger.debug("build_context_aware_plan interpret_query: %s", e)

    # 2) Resolve follow-up: get matched thread or session
    matched_thread_id: Optional[str] = None
    matched_session_id: Optional[str] = None
    follow_up_type = "none"
    try:
        from amazon_research.discovery import resolve_followup
        resolution = resolve_followup(source_query, workspace_id=workspace_id)
        matched_thread_id = resolution.get("matched_thread_id")
        matched_session_id = resolution.get("matched_session_id")
        follow_up_type = resolution.get("follow_up_type") or "none"
    except Exception as e:
        logger.debug("build_context_aware_plan resolve_followup: %s", e)

    is_follow_up = bool(matched_thread_id or matched_session_id)
    context_refs["matched_thread_id"] = matched_thread_id
    context_refs["matched_session_id"] = matched_session_id

    # 3) Enrich context from thread/session when available
    prior_intent = None
    prior_plan_ref = None
    prior_summary_ref = None
    prior_next_steps_ref = None
    prior_niche_cluster_market = None

    if matched_thread_id:
        try:
            from amazon_research.discovery import get_thread_summary
            summary = get_thread_summary(matched_thread_id, workspace_id=workspace_id)
            if summary:
                prior_niche_cluster_market = summary.get("thread_topic") or summary.get("thread_anchor")
                # Latest session may hold plan/summary refs
                latest_sid = summary.get("latest_session_reference")
                if latest_sid:
                    try:
                        from amazon_research.discovery.copilot_research_memory import get_session
                        sess = get_session(latest_sid, workspace_id=workspace_id)
                        if sess:
                            prior_intent = sess.get("interpreted_intent")
                            prior_plan_ref = sess.get("research_plan_ref")
                            prior_summary_ref = sess.get("insight_summary_ref")
                            steps_ref = sess.get("suggested_next_steps_ref")
                            if steps_ref:
                                prior_next_steps_ref = steps_ref[:5] if isinstance(steps_ref, list) else steps_ref
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("build_context_aware_plan get_thread_summary: %s", e)

    if matched_session_id and not prior_plan_ref:
        try:
            from amazon_research.discovery.copilot_research_memory import get_session
            sess = get_session(matched_session_id, workspace_id=workspace_id)
            if sess:
                prior_intent = prior_intent or sess.get("interpreted_intent")
                prior_plan_ref = prior_plan_ref or sess.get("research_plan_ref")
                prior_summary_ref = prior_summary_ref or sess.get("insight_summary_ref")
                steps_ref = sess.get("suggested_next_steps_ref")
                if steps_ref and not prior_next_steps_ref:
                    prior_next_steps_ref = steps_ref[:5] if isinstance(steps_ref, list) else steps_ref
        except Exception as e:
            logger.debug("build_context_aware_plan get_session: %s", e)

    context_refs["prior_interpreted_intent"] = prior_intent
    context_refs["prior_research_plan_ref"] = prior_plan_ref
    context_refs["prior_insight_summary_ref"] = prior_summary_ref
    context_refs["prior_recommended_next_steps_ref"] = prior_next_steps_ref
    context_refs["prior_niche_cluster_market"] = prior_niche_cluster_market

    # 4) Choose intent for plan: prefer prior intent on follow-up when continuation makes sense
    intent_for_plan = current_intent
    if is_follow_up and prior_intent and follow_up_type not in ("none",):
        intent_for_plan = prior_intent

    # 5) Build base plan via existing planner
    try:
        from amazon_research.discovery.copilot_planner import build_research_plan
        base_plan = build_research_plan(interpreted_intent=intent_for_plan)
    except Exception as e:
        logger.debug("build_context_aware_plan build_research_plan: %s", e)
        from amazon_research.discovery.copilot_planner import build_research_plan
        base_plan = build_research_plan(interpreted_intent=current_intent)

    # 6) Build planning rationale (explain fresh vs follow-up and context used)
    rationale_parts = [base_plan.get("planning_rationale_summary") or "Research plan generated."]
    if is_follow_up:
        rationale_parts.append("Follow-up/continuation: using prior context.")
        if matched_thread_id:
            rationale_parts.append(f"Matched thread: {matched_thread_id}.")
        if matched_session_id:
            rationale_parts.append(f"Matched session: {matched_session_id}.")
        if prior_niche_cluster_market:
            rationale_parts.append(f"Prior context: {str(prior_niche_cluster_market)[:60]}.")
    else:
        rationale_parts.append("Fresh research request; no prior thread/session matched.")
    planning_rationale = " ".join(rationale_parts)

    # 7) Assemble output
    return {
        "plan_id": base_plan.get("plan_id"),
        "source_query": source_query,
        "context_references_used": context_refs,
        "ordered_research_steps": base_plan.get("ordered_research_steps") or [],
        "planning_rationale": planning_rationale,
        "planning_rationale_summary": base_plan.get("planning_rationale_summary"),
        "timestamp": _ts(),
        "interpreted_intent": base_plan.get("interpreted_intent"),
        "is_follow_up": is_follow_up,
        "follow_up_type": follow_up_type,
    }


def get_context_aware_plan_for_query(query: str, *, workspace_id: Optional[int] = None) -> Dict[str, Any]:
    """Convenience: same as build_context_aware_plan(query, workspace_id=workspace_id)."""
    return build_context_aware_plan(query, workspace_id=workspace_id)
