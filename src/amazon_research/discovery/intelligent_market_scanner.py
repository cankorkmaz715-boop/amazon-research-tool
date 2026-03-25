"""
Step 122: Intelligent market scanner – prioritize high-opportunity scan targets.
Uses opportunity index, niche scoring, triggers. Integrates with scheduler, worker queue, crawler.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.intelligent_market_scanner")

TARGET_KEYWORD = "keyword"
TARGET_CATEGORY = "category"
TARGET_NICHE = "niche"
TARGET_CLUSTER = "cluster"

REASON_OPPORTUNITY_INDEX = "opportunity_index"
REASON_DEMAND_COMPETITION = "demand_vs_competition"
REASON_TRIGGER_SIGNAL = "trigger_signal"
REASON_READY_SEED = "ready_seed"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_intelligent_scan_plan(
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    max_keywords: int = 5,
    max_categories: int = 5,
    max_niches: int = 5,
    use_triggers: bool = True,
) -> Dict[str, Any]:
    """
    Build a prioritized scan plan from keywords, categories, and niches using opportunity and trigger signals.
    Returns: scan_plans (list of { scan_target, target_type, priority_score, scan_reason, timestamp, ... }),
    summary (total, by_type).
    """
    plans: List[Dict[str, Any]] = []
    ts = _now_iso()
    trigger_targets: Set[str] = set()

    if use_triggers:
        try:
            from amazon_research.discovery import evaluate_discovery_triggers
            result = evaluate_discovery_triggers(
                workspace_id=workspace_id,
                max_triggers=50,
                include_keyword_seeds=False,
                include_opportunity_alerts=True,
            )
            for t in result.get("triggers") or []:
                entity = (t.get("target_entity") or "").strip()
                if entity:
                    trigger_targets.add(entity)
        except Exception as e:
            logger.debug("intelligent_scanner triggers failed: %s", e)

    # Keywords from planner; priority from trigger boost or ready_seed
    try:
        from amazon_research.planner import build_keyword_scan_plan
        kw_plan = build_keyword_scan_plan(
            workspace_id=workspace_id,
            marketplace=marketplace,
            max_tasks=max_keywords,
        )
        for task in kw_plan.get("tasks") or []:
            kw = (task.get("keyword") or "").strip()
            if not kw:
                continue
            priority = 50.0
            reason = REASON_READY_SEED
            if kw in trigger_targets:
                priority += 30.0
                reason = REASON_TRIGGER_SIGNAL
            plans.append({
                "scan_target": kw,
                "target_type": TARGET_KEYWORD,
                "priority_score": round(priority, 1),
                "scan_reason": reason,
                "timestamp": ts,
                "seed_id": task.get("seed_id"),
                "marketplace": task.get("marketplace") or marketplace or "DE",
            })
    except Exception as e:
        logger.debug("intelligent_scanner keyword_plan failed: %s", e)

    # Categories from planner
    try:
        from amazon_research.planner import build_scan_plan
        cat_plan = build_scan_plan(
            workspace_id=workspace_id,
            marketplace=marketplace,
            max_tasks=max_categories,
        )
        for task in cat_plan.get("tasks") or []:
            url = (task.get("category_url") or "").strip()
            if not url:
                continue
            priority = 50.0
            reason = REASON_READY_SEED
            if url in trigger_targets:
                priority += 30.0
                reason = REASON_TRIGGER_SIGNAL
            plans.append({
                "scan_target": url,
                "target_type": TARGET_CATEGORY,
                "priority_score": round(priority, 1),
                "scan_reason": reason,
                "timestamp": ts,
                "seed_id": task.get("seed_id"),
                "marketplace": task.get("marketplace") or marketplace or "DE",
            })
    except Exception as e:
        logger.debug("intelligent_scanner category_plan failed: %s", e)

    # Niches/clusters from cluster cache + explorer (opportunity index, demand vs competition)
    try:
        from amazon_research.db import get_cluster_cache
        from amazon_research.explorer import explore_niches
        entry = get_cluster_cache(scope_key="default")
        clusters = (entry.get("clusters") or []) if entry else []
        if clusters:
            exp = explore_niches(clusters, use_db=True, limit=max_niches)
            niches = exp.get("niches") or []
            for n in niches[:max_niches]:
                cid = (n.get("cluster_id") or n.get("niche_id") or "").strip()
                if not cid:
                    continue
                opp = float(n.get("opportunity_index") or 0)
                demand = float(n.get("demand_score") or 0)
                comp = float(n.get("competition_score") or 0)
                priority = opp + 0.5 * (demand - comp)
                priority = max(0.0, min(100.0, 50.0 + priority))
                reason = REASON_OPPORTUNITY_INDEX if opp > 0 else REASON_DEMAND_COMPETITION
                plans.append({
                    "scan_target": cid,
                    "target_type": TARGET_NICHE,
                    "priority_score": round(priority, 1),
                    "scan_reason": reason,
                    "timestamp": ts,
                    "opportunity_index": opp,
                    "marketplace": marketplace or "DE",
                })
    except Exception as e:
        logger.debug("intelligent_scanner niches failed: %s", e)

    plans.sort(key=lambda p: (-(p.get("priority_score") or 0), p.get("scan_target") or ""))

    by_type: Dict[str, int] = {}
    for p in plans:
        k = p.get("target_type") or ""
        by_type[k] = by_type.get(k, 0) + 1

    return {
        "scan_plans": plans,
        "summary": {"total": len(plans), "by_type": by_type},
        "timestamp": ts,
    }


def to_scheduler_tasks(
    scan_plan_result: Dict[str, Any],
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convert intelligent scan plan to discovery-scheduler-style tasks (task_type, target_source, payload).
    Crawler-compatible: keyword_scan expects keyword; category_scan expects category_url; niche_discovery is one task.
    """
    plans = scan_plan_result.get("scan_plans") or []
    market = (marketplace or "DE").strip()
    tasks: List[Dict[str, Any]] = []
    seen_niche = False

    for p in plans:
        target_type = p.get("target_type") or ""
        scan_target = (p.get("scan_target") or "").strip()
        if not scan_target:
            continue
        if target_type == TARGET_KEYWORD:
            tasks.append({
                "task_type": "keyword_scan",
                "target_source": scan_target,
                "payload": {
                    "keyword": scan_target,
                    "marketplace": p.get("marketplace") or market,
                    "seed_id": p.get("seed_id"),
                    "workspace_id": workspace_id,
                },
            })
        elif target_type == TARGET_CATEGORY:
            tasks.append({
                "task_type": "category_scan",
                "target_source": scan_target,
                "payload": {
                    "category_url": scan_target,
                    "marketplace": p.get("marketplace") or market,
                    "seed_id": p.get("seed_id"),
                    "workspace_id": workspace_id,
                },
            })
        elif target_type in (TARGET_NICHE, TARGET_CLUSTER) and not seen_niche:
            tasks.append({
                "task_type": "niche_discovery",
                "target_source": scan_target,
                "payload": {"workspace_id": workspace_id, "marketplace": market},
            })
            seen_niche = True

    return tasks


def enqueue_intelligent_plan(
    scan_plan_result: Optional[Dict[str, Any]] = None,
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    scheduled_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Build intelligent plan (if not provided), convert to scheduler tasks, enqueue via worker queue.
    Returns job_ids and summary. Compatible with discovery scheduler and worker queue.
    """
    if scan_plan_result is None:
        scan_plan_result = build_intelligent_scan_plan(
            workspace_id=workspace_id,
            marketplace=marketplace,
        )
    tasks = to_scheduler_tasks(scan_plan_result, workspace_id=workspace_id, marketplace=marketplace)
    job_ids: List[int] = []
    by_type: Dict[str, int] = {}
    try:
        from amazon_research.db import enqueue_job
        for t in tasks:
            payload = t.get("payload") or {}
            jtype = t.get("task_type") or ""
            jid = enqueue_job(
                job_type=jtype,
                workspace_id=workspace_id,
                payload=payload,
                scheduled_at=scheduled_at,
            )
            job_ids.append(jid)
            by_type[jtype] = by_type.get(jtype, 0) + 1
    except Exception as e:
        logger.debug("enqueue_intelligent_plan failed: %s", e)
    return {
        "job_ids": job_ids,
        "summary": {"enqueued": len(job_ids), "by_type": by_type},
    }
