"""
Step 121: Autonomous discovery trigger engine – initiate discovery when signals appear.
Rule-based, deterministic. Uses opportunity alerts, keyword seeds, cluster cache.
Integrates with scheduler and worker queue.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.trigger_engine")

TRIGGER_TYPE_KEYWORD_SCAN = "keyword_scan"
TRIGGER_TYPE_CATEGORY_SCAN = "category_scan"
TRIGGER_TYPE_NICHE_DISCOVERY = "niche_discovery"
TRIGGER_TYPE_OPPORTUNITY_ALERT = "opportunity_alert"

TARGET_ENTITY_KEYWORD = "keyword"
TARGET_ENTITY_NICHE = "niche"
TARGET_ENTITY_CLUSTER = "cluster"

REASON_NEW_STRONG_CANDIDATE = "new_strong_candidate"
REASON_DEMAND_INCREASE = "demand_increase"
REASON_OPPORTUNITY_INCREASE = "opportunity_increase"
REASON_KEYWORD_EXPANSION = "keyword_expansion"
REASON_CLUSTER_OPPORTUNITY = "cluster_opportunity"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate_discovery_triggers(
    workspace_id: Optional[int] = None,
    max_triggers: int = 20,
    include_keyword_seeds: bool = True,
    include_opportunity_alerts: bool = True,
) -> Dict[str, Any]:
    """
    Evaluate signals and produce discovery triggers. Returns:
    triggers (list of { trigger_id, trigger_type, target_entity, reason_signal, timestamp }),
    summary (total, by_type), signals_used.
    """
    triggers: List[Dict[str, Any]] = []
    signals_used: List[str] = []

    # Opportunity alerts -> niche_discovery / opportunity_alert triggers
    if include_opportunity_alerts:
        try:
            from amazon_research.db import list_opportunity_alerts
            alerts = list_opportunity_alerts(workspace_id=workspace_id, limit=50)
            for a in alerts or []:
                if len(triggers) >= max_triggers:
                    break
                atype = (a.get("alert_type") or "").strip()
                entity = (a.get("target_entity") or "").strip()
                if not entity:
                    continue
                if atype in ("new_strong_candidate", "demand_increase", "opportunity_increase", "competition_drop", "trend_score_change"):
                    triggers.append({
                        "trigger_id": str(uuid.uuid4()),
                        "trigger_type": TRIGGER_TYPE_NICHE_DISCOVERY,
                        "target_entity": entity,
                        "target_entity_type": TARGET_ENTITY_CLUSTER,
                        "reason_signal": atype,
                        "timestamp": _now_iso(),
                    })
                    signals_used.append("opportunity_alerts")
            if triggers:
                triggers.append({
                    "trigger_id": str(uuid.uuid4()),
                    "trigger_type": TRIGGER_TYPE_OPPORTUNITY_ALERT,
                    "target_entity": "board",
                    "target_entity_type": TARGET_ENTITY_CLUSTER,
                    "reason_signal": "re_evaluate",
                    "timestamp": _now_iso(),
                })
        except Exception as e:
            logger.debug("trigger_engine opportunity_alerts failed: %s", e)

    # Ready keyword seeds -> keyword_scan triggers
    if include_keyword_seeds and len(triggers) < max_triggers:
        try:
            from amazon_research.db import get_ready_keyword_seeds
            seeds = get_ready_keyword_seeds(workspace_id=workspace_id, limit=5)
            for s in seeds or []:
                if len(triggers) >= max_triggers:
                    break
                kw = (s.get("keyword") or "").strip()
                if not kw:
                    continue
                triggers.append({
                    "trigger_id": str(uuid.uuid4()),
                    "trigger_type": TRIGGER_TYPE_KEYWORD_SCAN,
                    "target_entity": kw,
                    "target_entity_type": TARGET_ENTITY_KEYWORD,
                    "reason_signal": REASON_KEYWORD_EXPANSION,
                    "timestamp": _now_iso(),
                })
                signals_used.append("keyword_seeds")
        except Exception as e:
            logger.debug("trigger_engine keyword_seeds failed: %s", e)

    # Cluster cache -> optional niche_discovery trigger when we have clusters
    try:
        from amazon_research.db import get_cluster_cache
        entry = get_cluster_cache(scope_key="default")
        clusters = (entry.get("clusters") or []) if entry else []
        if clusters and len(triggers) < max_triggers and not any(t.get("reason_signal") == REASON_CLUSTER_OPPORTUNITY for t in triggers):
            c0 = clusters[0] if clusters else {}
            cid = (c0.get("cluster_id") or c0.get("label") or "default").strip()
            triggers.append({
                "trigger_id": str(uuid.uuid4()),
                "trigger_type": TRIGGER_TYPE_NICHE_DISCOVERY,
                "target_entity": cid,
                "target_entity_type": TARGET_ENTITY_CLUSTER,
                "reason_signal": REASON_CLUSTER_OPPORTUNITY,
                "timestamp": _now_iso(),
            })
            signals_used.append("cluster_cache")
    except Exception as e:
        logger.debug("trigger_engine cluster_cache failed: %s", e)

    by_type: Dict[str, int] = {}
    for t in triggers:
        k = t.get("trigger_type") or ""
        by_type[k] = by_type.get(k, 0) + 1

    return {
        "triggers": triggers,
        "summary": {"total": len(triggers), "by_type": by_type},
        "signals_used": list(dict.fromkeys(signals_used)),
    }


def enqueue_from_triggers(
    triggers: List[Dict[str, Any]],
    workspace_id: Optional[int] = None,
    marketplace: Optional[str] = None,
    scheduled_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Map triggers to worker jobs and enqueue. Deduplicates: at most one niche_discovery,
    one opportunity_alert; one keyword_scan per distinct keyword; one category_scan per distinct url.
    Returns job_ids, summary.
    """
    job_ids: List[int] = []
    enqueued_type: Dict[str, int] = {}
    seen_niche = False
    seen_alert = False
    seen_keywords: Set[str] = set()
    seen_category: Set[str] = set()

    try:
        from amazon_research.db import enqueue_job
    except ImportError:
        logger.warning("enqueue_from_triggers: enqueue_job not available")
        return {"job_ids": job_ids, "summary": {"enqueued": 0, "by_type": {}}}

    market = (marketplace or "DE").strip()

    for t in triggers:
        trigger_type = (t.get("trigger_type") or "").strip()
        target = (t.get("target_entity") or "").strip()

        if trigger_type == TRIGGER_TYPE_NICHE_DISCOVERY and not seen_niche:
            jid = enqueue_job(
                job_type="niche_discovery",
                workspace_id=workspace_id,
                payload={"workspace_id": workspace_id, "marketplace": market},
                scheduled_at=scheduled_at,
            )
            job_ids.append(jid)
            enqueued_type["niche_discovery"] = enqueued_type.get("niche_discovery", 0) + 1
            seen_niche = True
        elif trigger_type == TRIGGER_TYPE_OPPORTUNITY_ALERT and not seen_alert:
            jid = enqueue_job(
                job_type="opportunity_alert",
                workspace_id=workspace_id,
                payload={"workspace_id": workspace_id, "scope_key": "default"},
                scheduled_at=scheduled_at,
            )
            job_ids.append(jid)
            enqueued_type["opportunity_alert"] = enqueued_type.get("opportunity_alert", 0) + 1
            seen_alert = True
        elif trigger_type == TRIGGER_TYPE_KEYWORD_SCAN and target and target not in seen_keywords:
            seen_keywords.add(target)
            jid = enqueue_job(
                job_type="keyword_scan",
                workspace_id=workspace_id,
                payload={"keyword": target, "marketplace": market},
                scheduled_at=scheduled_at,
            )
            job_ids.append(jid)
            enqueued_type["keyword_scan"] = enqueued_type.get("keyword_scan", 0) + 1
        elif trigger_type == TRIGGER_TYPE_CATEGORY_SCAN and target and target not in seen_category:
            seen_category.add(target)
            jid = enqueue_job(
                job_type="category_scan",
                workspace_id=workspace_id,
                payload={"category_url": target, "marketplace": market},
                scheduled_at=scheduled_at,
            )
            job_ids.append(jid)
            enqueued_type["category_scan"] = enqueued_type.get("category_scan", 0) + 1

    return {
        "job_ids": job_ids,
        "summary": {"enqueued": len(job_ids), "by_type": enqueued_type},
    }
