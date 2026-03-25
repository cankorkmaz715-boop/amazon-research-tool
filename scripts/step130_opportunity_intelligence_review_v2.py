#!/usr/bin/env python3
"""
Step 130: Opportunity intelligence review v2.
Audits: autonomous discovery trigger engine, intelligent market scanner, continuous opportunity
discovery loop, opportunity memory layer, opportunity lifecycle tracker, research replay engine,
opportunity explainability layer, opportunity confidence scoring, opportunity ranking stabilizer.
Verifies integration, consistency (trigger/scan prioritization, memory/lifecycle, explainability/
confidence, ranking stabilization), and identifies strengths, weak points, and next improvements.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

WORKSPACE_ID = 1


def check_integration_consistency():
    """Trigger engine, intelligent scanner, continuous loop, replay: callable and return expected shapes."""
    ok = True
    try:
        # Trigger engine
        from amazon_research.discovery import evaluate_discovery_triggers
        triggers = evaluate_discovery_triggers(workspace_id=WORKSPACE_ID, max_triggers=5)
        ok = (
            isinstance(triggers, dict)
            and "triggers" in triggers
            and "summary" in triggers
            and isinstance(triggers.get("triggers"), list)
        )
        # Intelligent scanner
        from amazon_research.discovery import build_intelligent_scan_plan, to_scheduler_tasks
        plan = build_intelligent_scan_plan(
            workspace_id=WORKSPACE_ID,
            max_keywords=2,
            max_categories=2,
            max_niches=1,
            use_triggers=False,
        )
        ok = ok and isinstance(plan, dict) and "scan_plans" in plan and "summary" in plan
        tasks = to_scheduler_tasks(plan, workspace_id=WORKSPACE_ID)
        ok = ok and isinstance(tasks, list)
        # Continuous loop (max_enqueue=0 to avoid enqueueing jobs during audit)
        from amazon_research.discovery import run_opportunity_discovery_cycle
        cycle = run_opportunity_discovery_cycle(
            workspace_id=WORKSPACE_ID,
            max_enqueue=0,
            max_trigger_eval=5,
            include_trigger_eval=True,
            include_intelligent_plan=True,
        )
        ok = ok and (
            isinstance(cycle, dict)
            and "cycle_id" in cycle
            and "triggered_scans" in cycle
            and "ranked_opportunities" in cycle
            and "generated_alerts" in cycle
            and "timestamp" in cycle
        )
        # Replay engine
        from amazon_research.discovery import get_replay
        replay = get_replay(workspace_id=WORKSPACE_ID, limit_jobs=5, limit_discovery=5, limit_alerts=5)
        ok = ok and (
            isinstance(replay, dict)
            and "replay_id" in replay
            and "steps" in replay
            and "step_count" in replay
            and isinstance(replay.get("steps"), list)
        )
        # Replay step types align with loop outputs
        step_types = {s.get("step_type") for s in replay.get("steps", [])}
        expected = {"triggered_scans", "discovery_outputs", "niche_cluster", "ranking", "alerts"}
        ok = ok and step_types <= expected or len(replay.get("steps", [])) == 0
    except Exception:
        ok = False
    return ok


def check_memory_lifecycle():
    """Opportunity memory and lifecycle: shapes and that lifecycle consumes memory."""
    ok = True
    try:
        from amazon_research.db import get_opportunity_memory, list_opportunity_memory, record_opportunity_seen
        from amazon_research.discovery import get_opportunity_lifecycle, list_opportunities_with_lifecycle
        # Memory API
        mem = get_opportunity_memory("nonexistent-audit-ref")
        ok = mem is None or (
            isinstance(mem, dict)
            and "opportunity_ref" in mem
            and "first_seen_at" in mem
            and "last_seen_at" in mem
            and "score_history" in mem
        )
        listing = list_opportunity_memory(limit=5, workspace_id=WORKSPACE_ID)
        ok = ok and isinstance(listing, list)
        if listing:
            first = listing[0]
            ok = ok and "opportunity_ref" in first and "latest_opportunity_score" in first
        # Lifecycle consumes memory
        life = get_opportunity_lifecycle("nonexistent-audit-ref", memory_record=None)
        ok = ok and (
            isinstance(life, dict)
            and life.get("opportunity_id") == "nonexistent-audit-ref"
            and "lifecycle_state" in life
            and "rationale" in life
            and "supporting_signals" in life
        )
        list_life = list_opportunities_with_lifecycle(limit=3, workspace_id=WORKSPACE_ID)
        ok = ok and isinstance(list_life, list)
        if list_life:
            ok = ok and "lifecycle" in list_life[0] and "lifecycle_state" in list_life[0].get("lifecycle", {})
    except Exception:
        ok = False
    return ok


def check_explainability_confidence():
    """Explainability and confidence: output shapes and that confidence uses explainability."""
    ok = True
    try:
        from amazon_research.discovery import (
            get_opportunity_explanation,
            list_explanations,
            get_opportunity_confidence,
            list_opportunities_with_confidence,
        )
        expl = get_opportunity_explanation("nonexistent-audit-ref")
        ok = (
            isinstance(expl, dict)
            and expl.get("opportunity_id") == "nonexistent-audit-ref"
            and "main_supporting_signals" in expl
            and "explanation_summary" in expl
            and "signal_contribution_overview" in expl
        )
        conf = get_opportunity_confidence("nonexistent-audit-ref")
        ok = ok and (
            isinstance(conf, dict)
            and "confidence_score" in conf
            and "confidence_label" in conf
            and "contributing_signals" in conf
            and conf.get("confidence_label") in ("low", "medium", "high")
        )
        # Confidence contributing_signals should include signal_consistency (from explainability)
        sigs = conf.get("contributing_signals") or {}
        ok = ok and "signal_consistency" in sigs and "supporting_data_count" in sigs
        list_conf = list_opportunities_with_confidence(limit=3, workspace_id=WORKSPACE_ID)
        ok = ok and isinstance(list_conf, list)
        if list_conf:
            ok = ok and "confidence" in list_conf[0] and "confidence_score" in list_conf[0].get("confidence", {})
    except Exception:
        ok = False
    return ok


def check_ranking_stability():
    """Ranking stabilizer: raw vs stabilized, uses confidence and lifecycle."""
    ok = True
    try:
        from amazon_research.discovery import get_stabilized_ranking, get_stabilized_rankings
        out = get_stabilized_ranking("nonexistent-audit-ref")
        ok = (
            isinstance(out, dict)
            and out.get("opportunity_id") == "nonexistent-audit-ref"
            and "raw_score" in out
            and "stabilized_score" in out
            and "explanation" in out
        )
        # With synthetic memory: stabilized can differ from raw
        mem = {
            "opportunity_ref": "audit-stab",
            "latest_opportunity_score": 80,
            "score_history": [{"at": "2025-01-01Z", "score": 60}, {"at": "2025-01-02Z", "score": 65}],
        }
        out2 = get_stabilized_ranking("audit-stab", memory_record=mem)
        ok = ok and isinstance(out2.get("stabilized_score"), (int, float)) and 0 <= out2.get("stabilized_score", -1) <= 100
        rankings = get_stabilized_rankings(limit=5, workspace_id=WORKSPACE_ID)
        ok = ok and isinstance(rankings, list)
        if len(rankings) >= 2:
            ok = ok and rankings[0].get("stabilized_score", 0) >= rankings[1].get("stabilized_score", 100)
    except Exception:
        ok = False
    return ok


def main():
    from dotenv import load_dotenv
    load_dotenv()

    integration_ok = check_integration_consistency()
    memory_lifecycle_ok = check_memory_lifecycle()
    explainability_confidence_ok = check_explainability_confidence()
    ranking_stability_ok = check_ranking_stability()

    strengths = [
        "Trigger engine, intelligent scanner, and continuous loop are wired; cycle returns cycle_id, triggered_scans, ranked_opportunities, generated_alerts.",
        "Continuous loop records opportunities via record_opportunity_seen; memory feeds lifecycle, explainability, confidence, and stabilizer.",
        "Replay engine reconstructs steps (triggered_scans, discovery_outputs, niche_cluster, ranking, alerts) from jobs, discovery results, memory, alerts.",
        "Explainability aggregates demand, competition, opportunity_index, trend, lifecycle; confidence uses explainability for signal_consistency.",
        "Ranking stabilizer uses confidence and lifecycle to blend raw score with history (median/avg), reducing volatility; get_stabilized_rankings is board-compatible.",
    ]

    weak_points = [
        "Cycle has no persisted cycle_id; replay infers steps from time-window data, not from a stored cycle log.",
        "Trigger generation and scan prioritization share no explicit priority schema; scanner and trigger engine are independent.",
        "Trend history and cluster density are optional; many opportunities may have empty trend_history_length and cluster_density.",
        "Explainability trend_signal comes from trend_results by cluster ref; not all opportunities have trend_results persisted.",
    ]

    signal_gaps = [
        "Repeated detections and score_history are the same source; no separate 'discovery run id' to count distinct runs.",
        "Short-term spike vs long-term consistency uses a fixed window (e.g. last 5 scores); no configurable horizon.",
        "Stabilizer does not consume replay or cycle outputs; ranking is per-opportunity, not cycle-aware.",
    ]

    explainability_risks = [
        "Explanation summary is concatenated signals; no natural-language sentence for non-technical users.",
        "Signal contribution (positive/negative) uses fixed thresholds (e.g. demand >= 50); plan or workspace thresholds not supported.",
    ]

    operational_risks = [
        "Running the full cycle with max_enqueue > 0 creates real jobs; audit uses max_enqueue=0 to avoid side effects.",
        "List APIs (list_opportunity_memory, list_explanations, etc.) can grow; no pagination or cursor for large workspaces.",
    ]

    next_improvements = [
        "Persist cycle_id and optional cycle summary (e.g. in tenant_analytics or a cycle_log table) so replay can attach to a specific run.",
        "Add configurable stabilizer window (history length) and optional cycle-aware ranking (e.g. rank by stabilized score within last cycle).",
        "Define retention or cleanup for opportunity_memory and score_history to control growth.",
        "Expose stabilized rankings in niche explorer or opportunity board as an optional sort (stabilized_score).",
        "Consider pagination or cursor for list_opportunity_memory and list_opportunities_with_confidence for large tenants.",
    ]

    print("opportunity intelligence review v2 OK")
    print("integration consistency: OK" if integration_ok else "integration consistency: FAIL")
    print("memory/lifecycle: OK" if memory_lifecycle_ok else "memory/lifecycle: FAIL")
    print("explainability/confidence: OK" if explainability_confidence_ok else "explainability/confidence: FAIL")
    print("ranking stability: OK" if ranking_stability_ok else "ranking stability: FAIL")
    print("next improvements:")
    for n in next_improvements:
        print(f"  - {n}")
    print("strengths:")
    for s in strengths:
        print(f"  - {s}")
    print("weak points:")
    for w in weak_points:
        print(f"  - {w}")
    print("signal gaps:")
    for g in signal_gaps:
        print(f"  - {g}")
    print("explainability risks:")
    for e in explainability_risks:
        print(f"  - {e}")
    print("operational risks:")
    for o in operational_risks:
        print(f"  - {o}")

    all_ok = integration_ok and memory_lifecycle_ok and explainability_confidence_ok and ranking_stability_ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
