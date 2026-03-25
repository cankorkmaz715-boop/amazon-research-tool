"""
Step 123: Continuous opportunity discovery loop – one repeatable research cycle.
Orchestrates triggers, intelligent scanner, scan enqueue, niche discovery data, opportunity ranking, alerts.
Cycle caps and safety limits; no infinite crawling.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.continuous_loop")

DEFAULT_MAX_ENQUEUE = 5
DEFAULT_MAX_TRIGGERS = 15


def run_opportunity_discovery_cycle(
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    max_enqueue: int = DEFAULT_MAX_ENQUEUE,
    max_trigger_eval: int = DEFAULT_MAX_TRIGGERS,
    include_trigger_eval: bool = True,
    include_intelligent_plan: bool = True,
) -> Dict[str, Any]:
    """
    Run one discovery cycle: evaluate triggers, build intelligent plan, enqueue capped scans,
    gather clusters, rank opportunities, evaluate alerts. Returns structured cycle output.
    Cycle caps: max_enqueue jobs, max_trigger_eval for trigger evaluation. No infinite crawl.
    """
    cycle_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    out: Dict[str, Any] = {
        "cycle_id": cycle_id,
        "triggered_scans": [],
        "discovered_candidates": [],
        "ranked_opportunities": [],
        "generated_alerts": [],
        "timestamp": ts,
    }
    market = (marketplace or "DE").strip()

    # 1) Autonomous discovery triggers
    triggers_result: Dict[str, Any] = {}
    if include_trigger_eval:
        try:
            from amazon_research.discovery import evaluate_discovery_triggers
            triggers_result = evaluate_discovery_triggers(
                workspace_id=workspace_id,
                max_triggers=max_trigger_eval,
                include_keyword_seeds=True,
                include_opportunity_alerts=True,
            )
        except Exception as e:
            logger.debug("cycle triggers failed: %s", e)

    # 2) Intelligent scan plan and enqueue (capped)
    if include_intelligent_plan and max_enqueue > 0:
        try:
            from amazon_research.discovery import build_intelligent_scan_plan, to_scheduler_tasks
            from amazon_research.db import enqueue_job
            plan = build_intelligent_scan_plan(
                workspace_id=workspace_id,
                marketplace=market,
                max_keywords=min(3, max_enqueue),
                max_categories=min(3, max_enqueue),
                max_niches=min(2, max_enqueue),
                use_triggers=bool(triggers_result),
            )
            tasks = to_scheduler_tasks(plan, workspace_id=workspace_id, marketplace=market)
            enqueued = 0
            for t in tasks:
                if enqueued >= max_enqueue:
                    break
                jtype = t.get("task_type") or ""
                payload = t.get("payload") or {}
                target = payload.get("keyword") or payload.get("category_url") or t.get("target_source") or ""
                jid = enqueue_job(
                    job_type=jtype,
                    workspace_id=workspace_id,
                    payload=payload,
                )
                out["triggered_scans"].append({
                    "job_id": jid,
                    "job_type": jtype,
                    "target": target or "(niche_discovery)",
                })
                enqueued += 1
        except Exception as e:
            logger.debug("cycle enqueue failed: %s", e)

    # 3) Clusters and discovered candidates (from cache; no crawl in-cycle)
    try:
        from amazon_research.db import get_cluster_cache
        entry = get_cluster_cache(scope_key="default")
        clusters = (entry.get("clusters") or []) if entry else []
        for c in clusters:
            cid = (c.get("cluster_id") or c.get("label") or "").strip()
            if cid:
                out["discovered_candidates"].append({"cluster_id": cid, "label": c.get("label")})
            asins = c.get("member_asins") or []
            for a in asins:
                if isinstance(a, str) and a.strip():
                    out["discovered_candidates"].append({"asin": a.strip(), "cluster_id": c.get("cluster_id")})
    except Exception as e:
        logger.debug("cycle cluster cache failed: %s", e)

    # 4) Ranked opportunities (explorer)
    try:
        from amazon_research.db import get_cluster_cache
        from amazon_research.explorer import explore_niches
        entry = get_cluster_cache(scope_key="default")
        clusters = (entry.get("clusters") or []) if entry else []
        if clusters:
            exp = explore_niches(clusters, use_db=True, limit=50)
            out["ranked_opportunities"] = exp.get("niches") or []
            for n in out.get("ranked_opportunities") or []:
                try:
                    from amazon_research.db import record_opportunity_seen
                    ref = (n.get("cluster_id") or n.get("niche_id") or "").strip()
                    if ref:
                        record_opportunity_seen(
                            ref,
                            context={"label": n.get("label"), "demand_score": n.get("demand_score"), "competition_score": n.get("competition_score")},
                            latest_opportunity_score=float(n.get("opportunity_index") or 0),
                            workspace_id=workspace_id,
                        )
                except Exception:
                    pass
    except Exception as e:
        logger.debug("cycle explore_niches failed: %s", e)

    # 5) Alert generation (from current ranked opportunities)
    try:
        from amazon_research.alerts import evaluate_opportunity_alerts
        current = out.get("ranked_opportunities") or []
        alert_result = evaluate_opportunity_alerts(current, previous_entries=None)
        out["generated_alerts"] = alert_result.get("alerts") or []
    except Exception as e:
        logger.debug("cycle alerts failed: %s", e)

    return out
