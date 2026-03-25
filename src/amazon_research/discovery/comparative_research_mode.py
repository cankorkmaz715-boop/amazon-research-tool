"""
Step 149: Copilot comparative research mode – analyze multiple research targets in parallel.
Supports niche vs niche, keyword vs keyword, cluster vs cluster, market vs market.
Deterministic, rule-based. Integrates with context-aware planner, guided execution, insight summarizer.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.comparative_research_mode")

# Target type constants
TARGET_NICHE = "niche"
TARGET_KEYWORD = "keyword"
TARGET_CLUSTER = "product_cluster"
TARGET_MARKET = "market"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _target_to_query(target: Union[str, Dict[str, Any]], index: int) -> str:
    """Turn a comparison target into a research query string. Rule-based."""
    if isinstance(target, str):
        return target.strip() or f"Research target {index + 1}"
    t = target if isinstance(target, dict) else {}
    ttype = (t.get("type") or "niche").strip().lower()
    label = (t.get("label") or t.get("ref") or "").strip() or f"target_{index + 1}"
    if ttype == TARGET_NICHE:
        return f"Find niches in {label}"
    if ttype == TARGET_KEYWORD:
        return f"Explore keywords for {label}"
    if ttype == TARGET_CLUSTER:
        return f"Analyze product cluster {label}"
    if ttype == TARGET_MARKET:
        return f"Research market {label}"
    return label


def _run_guided_execution_for_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Execute plan step-by-step (iterate steps, collect outcome). No external calls; deterministic."""
    steps = plan.get("ordered_research_steps") or []
    step_results = []
    for s in steps:
        step_results.append({
            "step_order": s.get("step_order"),
            "step_type": s.get("step_type"),
            "engines": s.get("suggested_engines") or [],
        })
    return {
        "plan_id": plan.get("plan_id"),
        "interpreted_intent": plan.get("interpreted_intent"),
        "steps_completed": len(step_results),
        "step_results": step_results,
    }


def run_comparative_research(
    targets: List[Union[str, Dict[str, Any]]],
    *,
    workspace_id: Optional[int] = None,
    use_context_aware_planning: bool = True,
) -> Dict[str, Any]:
    """
    Analyze multiple research targets in parallel (processed sequentially; results aggregated).
    For each target: generate plan, run guided execution, collect insights.
    Returns: comparison_id, targets_compared, summary_metrics_per_target, comparative_insight_summary,
    suggested_best_candidate, timestamp.
    """
    comparison_id = f"compare-{uuid.uuid4().hex[:12]}"
    targets_compared = []
    summary_metrics_per_target: List[Dict[str, Any]] = []
    insights_per_target: List[Dict[str, Any]] = []

    for i, target in enumerate(targets):
        label = target if isinstance(target, str) else (target.get("label") or target.get("ref") or f"target_{i + 1}")
        targets_compared.append({"index": i + 1, "label": str(label), "target": target})
        query = _target_to_query(target, i)

        # 1) Generate research plan (context-aware or plain)
        plan: Optional[Dict[str, Any]] = None
        try:
            if use_context_aware_planning:
                from amazon_research.discovery import build_context_aware_plan
                plan = build_context_aware_plan(query, workspace_id=workspace_id)
            else:
                from amazon_research.discovery import get_plan_for_query
                plan = get_plan_for_query(query)
        except Exception as e:
            logger.debug("run_comparative_research plan for target %s: %s", i, e)
            try:
                from amazon_research.discovery import get_plan_for_query
                plan = get_plan_for_query(query)
            except Exception:
                plan = None

        if not plan:
            summary_metrics_per_target.append({"target_index": i + 1, "steps_completed": 0, "insight_count": 0, "plan_id": None})
            insights_per_target.append({})
            continue

        # 2) Run guided execution (step-by-step)
        execution_output = _run_guided_execution_for_plan(plan)

        # 3) Collect insights (insight summarizer)
        insight_summary: Dict[str, Any] = {}
        try:
            from amazon_research.discovery import build_insight_summary, summarize_guided_execution
            insight_summary = build_insight_summary(
                execution_output,
                plan_id=plan.get("plan_id"),
                workspace_id=workspace_id,
                include_opportunity_insights=False,
                include_recommendations=False,
            )
        except Exception as e:
            logger.debug("run_comparative_research build_insight_summary: %s", e)
            try:
                insight_summary = summarize_guided_execution(plan, steps_executed=execution_output.get("step_results") or [], workspace_id=workspace_id)
            except Exception:
                insight_summary = {"key_insights": [], "main_supporting_signals": {}}

        insights_per_target.append(insight_summary)
        key_insights = insight_summary.get("key_insights") or []
        signals = insight_summary.get("main_supporting_signals") or {}
        steps_completed = execution_output.get("steps_completed") or 0
        summary_metrics_per_target.append({
            "target_index": i + 1,
            "label": str(label),
            "steps_completed": steps_completed,
            "insight_count": len(key_insights),
            "plan_id": plan.get("plan_id"),
            "interpreted_intent": plan.get("interpreted_intent"),
            "signal_keys": list(signals.keys()) if isinstance(signals, dict) else [],
        })

    # 4) Comparative insight summary (rule-based)
    parts = []
    for i, m in enumerate(summary_metrics_per_target):
        label = m.get("label") or targets_compared[i].get("label") or f"Target {i + 1}"
        steps = m.get("steps_completed") or 0
        insights = m.get("insight_count") or 0
        parts.append(f"{label}: {steps} step(s) completed, {insights} key insight(s).")
    comparative_insight_summary = " ".join(parts) if parts else "No targets processed."

    # 5) Suggested best candidate (rule-based: most insights, then most steps, then first)
    best_index = 0
    best_score = -1
    for i, m in enumerate(summary_metrics_per_target):
        score = (m.get("insight_count") or 0) * 2 + (m.get("steps_completed") or 0)
        if score > best_score:
            best_score = score
            best_index = i
    best_label = summary_metrics_per_target[best_index].get("label") if best_index < len(summary_metrics_per_target) else (targets_compared[best_index].get("label") if best_index < len(targets_compared) else "target_1")
    suggested_best_candidate = {
        "target_index": best_index + 1,
        "label": best_label,
        "rationale": f"Highest combined insight count and steps completed (score {best_score}).",
    }

    return {
        "comparison_id": comparison_id,
        "targets_compared": targets_compared,
        "summary_metrics_per_target": summary_metrics_per_target,
        "comparative_insight_summary": comparative_insight_summary,
        "suggested_best_candidate": suggested_best_candidate,
        "timestamp": _ts(),
        "insights_per_target": insights_per_target,
    }


def compare_targets(
    targets: List[Union[str, Dict[str, Any]]],
    *,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Convenience: same as run_comparative_research with context-aware planning enabled."""
    return run_comparative_research(targets, workspace_id=workspace_id, use_context_aware_planning=True)
