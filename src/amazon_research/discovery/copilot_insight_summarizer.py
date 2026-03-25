"""
Step 144: Copilot insight summarizer – turn structured research outputs into concise insight summaries.
Uses guided execution, opportunity board, explainability, confidence, lifecycle. Rule-based, human-readable.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.copilot_insight_summarizer")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_insight_summary(
    execution_output: Optional[Dict[str, Any]] = None,
    *,
    plan_id: Optional[str] = None,
    request_id: Optional[str] = None,
    workspace_id: Optional[int] = None,
    include_opportunity_insights: bool = True,
    include_recommendations: bool = True,
    limit_opportunities: int = 10,
) -> Dict[str, Any]:
    """
    Turn structured research outputs into a concise insight summary.

    Inputs (any combination):
    - execution_output: result of guided research execution (plan_id, steps_completed, step_results, interpreted_intent)
    - plan_id / request_id: target research request or execution id

    Produces: summary_id, target_research_request_id, key_insights, main_supporting_signals,
    risk_uncertainty_notes, suggested_next_steps, timestamp.
    """
    summary_id = f"summary-{uuid.uuid4().hex[:12]}"
    target_id = request_id or plan_id or (execution_output or {}).get("plan_id") or ""
    out: Dict[str, Any] = {
        "summary_id": summary_id,
        "target_research_request_id": target_id,
        "target_execution_id": target_id,
        "key_insights": [],
        "main_supporting_signals": {},
        "risk_uncertainty_notes": [],
        "suggested_next_steps": [],
        "timestamp": _ts(),
    }

    # From execution output (guided research)
    if execution_output:
        intent = execution_output.get("interpreted_intent") or ""
        steps_completed = execution_output.get("steps_completed") or 0
        step_results = execution_output.get("step_results") or []
        if intent:
            out["key_insights"].append(f"Research intent: {intent.replace('_', ' ')}.")
        if steps_completed > 0:
            out["key_insights"].append(f"Completed {steps_completed} research step(s).")
        if step_results:
            step_types = [s.get("step_type") or "step" for s in step_results]
            out["main_supporting_signals"]["execution_steps"] = step_types

    if plan_id and not out["target_research_request_id"]:
        out["target_research_request_id"] = plan_id
        out["target_execution_id"] = plan_id

    # Enrich from opportunity board / explainability / confidence / lifecycle
    if include_opportunity_insights and (workspace_id is not None or execution_output):
        try:
            from amazon_research.discovery import (
                list_explanations,
                list_opportunities_with_confidence,
                list_opportunities_with_lifecycle,
            )
            ws = workspace_id
            if ws is None and execution_output:
                ws = execution_output.get("workspace_id")
            limit = limit_opportunities
            explanations = list_explanations(limit=limit, workspace_id=ws)
            with_conf = list_opportunities_with_confidence(limit=limit, workspace_id=ws)
            with_life = list_opportunities_with_lifecycle(limit=limit, workspace_id=ws)

            # Key insights from explanations
            for ex in explanations[:5]:
                summary = (ex.get("explanation_summary") or "").strip()
                if summary:
                    out["key_insights"].append(summary[:200] + ("..." if len(summary) > 200 else ""))
            # Supporting signals aggregate
            if explanations:
                signals: Dict[str, Any] = out.get("main_supporting_signals") or {}
                opp_ids = [e.get("opportunity_id") for e in explanations if e.get("opportunity_id")]
                if opp_ids:
                    signals["opportunity_count"] = len(opp_ids)
                    signals["sample_opportunities"] = opp_ids[:5]
                out["main_supporting_signals"] = signals

            # Risk / uncertainty from low confidence and weakening lifecycle
            for c in with_conf:
                label = (c.get("confidence_label") or "").lower()
                if label == "low":
                    ref = c.get("opportunity_id") or "unknown"
                    out["risk_uncertainty_notes"].append(f"Low confidence for opportunity {ref}.")
            for l in with_life:
                state = (l.get("lifecycle_state") or "").lower()
                if state in ("weakening", "fading", "inactive"):
                    ref = l.get("opportunity_id") or "unknown"
                    out["risk_uncertainty_notes"].append(f"Lifecycle {state} for {ref}.")
        except Exception as e:
            logger.debug("build_insight_summary opportunity enrichment failed: %s", e)

    # Suggested next steps from recommendations
    if include_recommendations:
        try:
            from amazon_research.discovery import get_recommendations
            from amazon_research.discovery import get_plan_for_query
            ws = workspace_id
            if ws is None and execution_output:
                ws = execution_output.get("workspace_id")
            recos = get_recommendations(workspace_id=ws, limit=5)
            for r in recos:
                rec_type = r.get("recommendation_type") or "review"
                expl = (r.get("explanation") or "").strip()
                entity = r.get("target_entity") or {}
                ref = entity.get("ref") or entity.get("id") or ""
                step = f"{rec_type.replace('_', ' ')}"
                if ref:
                    step += f" ({ref})"
                if expl:
                    step += f": {expl[:80]}"
                out["suggested_next_steps"].append(step)
            if not recos:
                intent = (execution_output or {}).get("interpreted_intent") or ""
                if intent == "keyword_exploration":
                    out["suggested_next_steps"].append("Run keyword scan and review search volume.")
                elif intent == "niche_discovery":
                    out["suggested_next_steps"].append("Run niche discovery and review clusters.")
                else:
                    out["suggested_next_steps"].append("Review opportunity board and run next research step.")
        except Exception as e:
            logger.debug("build_insight_summary recommendations failed: %s", e)
            out["suggested_next_steps"].append("Review research dashboard and opportunity board.")

    # Deduplicate and cap lists
    out["key_insights"] = list(dict.fromkeys(out["key_insights"]))[:15]
    out["risk_uncertainty_notes"] = list(dict.fromkeys(out["risk_uncertainty_notes"]))[:10]
    out["suggested_next_steps"] = list(dict.fromkeys(out["suggested_next_steps"]))[:10]

    return out


def summarize_guided_execution(
    plan: Dict[str, Any],
    *,
    workspace_id: Optional[int] = None,
    steps_executed: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Convenience: build an execution-style payload from a plan and optional step results,
    then return the insight summary. Compatible with copilot planner + guided execution flow.
    """
    steps = steps_executed or []
    execution_output = {
        "plan_id": plan.get("plan_id"),
        "interpreted_intent": plan.get("interpreted_intent"),
        "steps_completed": len(steps),
        "step_results": steps,
        "workspace_id": workspace_id,
    }
    return build_insight_summary(
        execution_output,
        plan_id=plan.get("plan_id"),
        workspace_id=workspace_id,
    )
