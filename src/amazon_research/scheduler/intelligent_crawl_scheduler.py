"""
Step 164: Intelligent crawl scheduler – prioritize crawl targets by research value.
Uses trend score, opportunity score, confidence, staleness, workspace interest, discovery triggers.
Integrates with discovery scheduler, intelligent market scanner, worker queue, scraper reliability.
Lightweight, deterministic, rule-based. Extensible for adaptive optimization.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("scheduler.intelligent_crawl_scheduler")

TARGET_CATEGORY = "category"
TARGET_KEYWORD = "keyword"
TARGET_ASIN_REFRESH = "asin_refresh"
TARGET_NICHE = "niche"
TARGET_CLUSTER = "cluster"

# Staleness: hours after which we boost priority
STALE_HOURS = 24.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _hours_since(dt: Optional[datetime]) -> Optional[float]:
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (now - dt).total_seconds() / 3600.0
    return delta


def get_intelligent_crawl_schedule(
    workspace_id: Optional[int] = None,
    *,
    limit: int = 50,
    include_categories: bool = True,
    include_keywords: bool = True,
    include_niches: bool = True,
    include_opportunity_refresh: bool = True,
    use_triggers: bool = True,
) -> List[Dict[str, Any]]:
    """
    Build a prioritized list of crawl targets. Each item: target_id, target_type, priority_score,
    scheduling_rationale, timestamp. Uses opportunity score, confidence, staleness, triggers.
    Does not enqueue; use enqueue_intelligent_crawl_schedule to push to worker queue.
    """
    results: List[Dict[str, Any]] = []
    ts = _now_iso()
    trigger_targets: set = set()

    if use_triggers:
        try:
            from amazon_research.discovery import evaluate_discovery_triggers
            r = evaluate_discovery_triggers(workspace_id=workspace_id, max_triggers=50, include_opportunity_alerts=True)
            for t in r.get("triggers") or []:
                entity = (t.get("target_entity") or "").strip()
                if entity:
                    trigger_targets.add(entity)
        except Exception as e:
            logger.debug("intelligent_crawl_scheduler triggers: %s", e)

    # 1) Intelligent scan plan (categories, keywords, niches) – already prioritized
    try:
        from amazon_research.discovery.intelligent_market_scanner import build_intelligent_scan_plan
        plan = build_intelligent_scan_plan(
            workspace_id=workspace_id,
            max_keywords=limit,
            max_categories=limit,
            max_niches=limit,
            use_triggers=use_triggers,
        )
        for p in plan.get("scan_plans") or []:
            target_type = (p.get("target_type") or "cluster").strip().lower()
            scan_target = (p.get("scan_target") or "").strip()
            if not scan_target:
                continue
            priority = float(p.get("priority_score") or 50.0)
            reason = (p.get("scan_reason") or "intelligent_plan").strip()
            if scan_target in trigger_targets:
                priority += 15.0
                reason = "trigger_signal"
            rationale = f"{reason}; priority {priority:.0f}"
            if target_type == "keyword" and include_keywords:
                results.append({
                    "target_id": scan_target,
                    "target_type": TARGET_KEYWORD,
                    "priority_score": round(min(100.0, priority), 1),
                    "scheduling_rationale": rationale,
                    "timestamp": ts,
                })
            elif target_type == "category" and include_categories:
                results.append({
                    "target_id": scan_target,
                    "target_type": TARGET_CATEGORY,
                    "priority_score": round(min(100.0, priority), 1),
                    "scheduling_rationale": rationale,
                    "timestamp": ts,
                })
            elif target_type in ("niche", "cluster") and include_niches:
                results.append({
                    "target_id": scan_target,
                    "target_type": TARGET_NICHE if target_type == "niche" else TARGET_CLUSTER,
                    "priority_score": round(min(100.0, priority), 1),
                    "scheduling_rationale": rationale,
                    "timestamp": ts,
                })
    except Exception as e:
        logger.debug("intelligent_crawl_scheduler scan_plan: %s", e)

    # 2) Opportunity memory – refresh targets with staleness and opportunity score
    if include_opportunity_refresh:
        try:
            from amazon_research.db import list_opportunity_memory
            from amazon_research.discovery import get_opportunity_confidence
            rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
            for mem in rows:
                ref = (mem.get("opportunity_ref") or "").strip()
                if not ref:
                    continue
                last_seen = _parse_dt(mem.get("last_seen_at"))
                hours = _hours_since(last_seen)
                score = mem.get("latest_opportunity_score")
                opp_score = float(score) if score is not None else 50.0
                priority = 40.0 + (opp_score * 0.3)
                rationale_parts = [f"opportunity_score={opp_score:.0f}"]
                if hours is not None and hours > STALE_HOURS:
                    priority += min(25.0, hours / 2.0)
                    rationale_parts.append(f"stale {hours:.0f}h")
                try:
                    conf = get_opportunity_confidence(ref, workspace_id=workspace_id, memory_record=mem)
                    cl = (conf.get("confidence_label") or "").strip().lower()
                    if cl == "high":
                        priority += 5.0
                    rationale_parts.append(f"confidence={cl or 'unknown'}")
                except Exception:
                    pass
                results.append({
                    "target_id": ref,
                    "target_type": TARGET_CLUSTER,
                    "priority_score": round(min(100.0, priority), 1),
                    "scheduling_rationale": "; ".join(rationale_parts),
                    "timestamp": ts,
                })
        except Exception as e:
            logger.debug("intelligent_crawl_scheduler opportunity_memory: %s", e)

    # Dedupe by target_id + target_type, keep highest priority
    by_key: Dict[tuple, Dict[str, Any]] = {}
    for r in results:
        key = (r.get("target_type"), (r.get("target_id") or "")[:200])
        if key not in by_key or (r.get("priority_score") or 0) > (by_key[key].get("priority_score") or 0):
            by_key[key] = r
    ordered = list(by_key.values())
    ordered.sort(key=lambda x: (-(x.get("priority_score") or 0), x.get("target_id") or ""))
    return ordered[:limit]


def to_scheduler_tasks(
    schedule: List[Dict[str, Any]],
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convert intelligent crawl schedule to discovery-scheduler-style tasks for enqueue_job."""
    market = (marketplace or "DE").strip()
    tasks: List[Dict[str, Any]] = []
    seen_niche = False
    for s in schedule:
        target_type = s.get("target_type") or ""
        target_id = (s.get("target_id") or "").strip()
        if not target_id:
            continue
        if target_type == TARGET_KEYWORD:
            tasks.append({
                "task_type": "keyword_scan",
                "target_source": target_id,
                "payload": {"keyword": target_id, "marketplace": market, "workspace_id": workspace_id},
            })
        elif target_type == TARGET_CATEGORY:
            tasks.append({
                "task_type": "category_scan",
                "target_source": target_id,
                "payload": {"category_url": target_id, "marketplace": market, "workspace_id": workspace_id},
            })
        elif target_type in (TARGET_NICHE, TARGET_CLUSTER) and not seen_niche:
            tasks.append({
                "task_type": "niche_discovery",
                "target_source": target_id,
                "payload": {"workspace_id": workspace_id, "marketplace": market, "cluster_id": target_id},
            })
            seen_niche = True
    return tasks


def enqueue_intelligent_crawl_schedule(
    schedule: Optional[List[Dict[str, Any]]] = None,
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    limit: int = 30,
    scheduled_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Build schedule (if not provided), convert to tasks, enqueue via worker queue.
    Compatible with discovery scheduler and worker queue. Optionally check scraper reliability.
    """
    if schedule is None:
        schedule = get_intelligent_crawl_schedule(workspace_id=workspace_id, limit=limit)
    tasks = to_scheduler_tasks(schedule, workspace_id=workspace_id, marketplace=marketplace)
    job_ids: List[int] = []
    by_type: Dict[str, int] = {}
    try:
        from amazon_research.db import enqueue_job
        for t in tasks:
            payload = t.get("payload") or {}
            jtype = t.get("task_type") or ""
            jid = enqueue_job(job_type=jtype, workspace_id=workspace_id, payload=payload, scheduled_at=scheduled_at)
            if jid:
                job_ids.append(jid)
                by_type[jtype] = by_type.get(jtype, 0) + 1
    except Exception as e:
        logger.debug("enqueue_intelligent_crawl_schedule: %s", e)
    return {"job_ids": job_ids, "summary": {"enqueued": len(job_ids), "by_type": by_type}}
